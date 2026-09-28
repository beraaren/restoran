"""FastAPI sunucusu — ingestion + panel API + canlı yayın.

Endpoint'ler:
  POST /ingest/pos      PosEvent (tek liste kabul eder; idempotent)
  POST /ingest/vision   VisionEvent (CLI runner buraya pushlar)
  GET  /anomalies       anomali akışı (filter: kind, since)
  GET  /state           aktör durumları + sayaçlar (panel KPI'ları)
  GET  /events/recent   ham event akışı (canlı şerit)
  GET  /scene           zone config
  PUT  /scene           zone config güncelle (çizim aracından)
  GET  /health

Not: timestamp'ler UTC-ms; kalibrasyon modu DATABASE_URL ayarıyla başlar.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from ..contracts.events import PosEvent, VisionEvent
from ..config.zones import SceneConfig
from ..reconcile.engine import Anomaly, Reconciler, RuleWindows
from ..states.machine import StateChange
from ..states.actors import ACTORS
from ..states.signals import route_pos, route_vision
from ..store.db import (AnomalyRow, PosEventRow, SessionLocal, VisionEventRow,
                       init_db, store_anomaly, store_pos, store_vision)
from .admin import router as admin_router
from ..auth.admin_router import router as identity_admin_router
from ..auth.login import router as auth_login_router
from ..auth.me import router as auth_me_router

SCENE_PATH = Path(os.environ.get("SCENE_PATH", "config/scene.demo.json"))
CALIBRATION_S = int(os.environ.get("CALIBRATION_S", "0"))  # demo'da kapalı


class Hub:
    """WebSocket broadcast + son event'lerin dairesel tamponu."""

    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()
        self.recent: deque = deque(maxlen=300)
        self.counts = {"plates_out": 0, "tickets": 0}

    async def join(self, ws: WebSocket) -> None:
        await ws.accept()
        self.clients.add(ws)

    def leave(self, ws: WebSocket) -> None:
        self.clients.discard(ws)

    async def publish(self, kind: str, data: dict) -> None:
        msg = {"kind": kind, "at_ms": int(time.time() * 1000), "data": data}
        self.recent.append(msg)
        dead = set()
        for ws in self.clients:
            try:
                await ws.send_json(msg)
            except Exception:
                dead.add(ws)
        self.clients -= dead


hub = Hub()
state: dict = {}


def load_scene() -> SceneConfig:
    if SCENE_PATH.exists():
        return SceneConfig.model_validate(json.loads(SCENE_PATH.read_text()))
    return SceneConfig(venue_id="demo")


def bootstrap() -> None:
    init_db()
    scene = load_scene()
    state["scene"] = scene
    state["reconciler"] = Reconciler(
        RuleWindows.from_env(), calibrating=time.time() - START_TS < CALIBRATION_S)
    state["zone_to_table"] = {
        z.zone_id: z.pos_table_id
        for cam in scene.cameras for z in cam.zones
        if z.kind == "table" and z.pos_table_id}


START_TS = time.time()


async def evaluator_loop() -> None:
    while True:
        await asyncio.sleep(5)
        r: Reconciler = state["reconciler"]
        now = int(time.time() * 1000)
        anomalies = r.evaluate(now, state["zone_to_table"])
        for a in anomalies:
            s = SessionLocal()
            try:
                store_anomaly(s, a)
                s.commit()
            finally:
                s.close()
            await hub.publish("anomaly", _anomaly_dict(a))


@asynccontextmanager
async def lifespan(app: FastAPI):
    bootstrap()
    task = asyncio.create_task(evaluator_loop())
    yield
    task.cancel()


app = FastAPI(title="Restoran Akış İzleme", lifespan=lifespan)
app.include_router(admin_router)
app.include_router(auth_login_router)
app.include_router(auth_me_router)
app.include_router(identity_admin_router)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])


def _anomaly_dict(a: Anomaly | AnomalyRow) -> dict:
    if isinstance(a, Anomaly):
        d = {"anomaly_id": a.anomaly_id, "kind": a.kind, "severity": a.severity,
             "occurred_at_ms": a.occurred_at_ms, "amount_tl": str(a.amount_tl) if a.amount_tl else None,
             "title": a.title, "detail": a.detail, "table_id": a.table_id,
             "track_id": a.track_id, "suppressed": a.suppressed}
    else:
        d = {"anomaly_id": a.anomaly_id, "kind": a.kind, "severity": a.severity,
             "occurred_at_ms": a.occurred_at_ms,
             "amount_tl": str(a.amount_tl) if a.amount_tl else None,
             "title": a.title, "detail": a.detail, "table_id": a.table_id,
             "track_id": a.track_id, "suppressed": a.suppressed}
    return d


def _apply_signals(signals, evidence: dict) -> None:
    for sig in signals:
        sm = ACTORS.get(sig.actor_type)
        if not sm:
            continue
        ch = sm.apply(sig.actor_id, sig.name, sig.at_ms, {**evidence, **sig.evidence})
        if ch:
            asyncio.get_running_loop().create_task(hub.publish("state_change", {
                "actor_type": ch.actor_type, "actor_id": ch.actor_id,
                "old": ch.old, "new": ch.new, "at_ms": ch.at_ms,
                "signal": ch.signal}))


# ---------------------------------------------------------------- ingestion
@app.post("/ingest/pos")
async def ingest_pos(events: list[PosEvent]):
    r: Reconciler = state["reconciler"]
    res = {"accepted": 0, "duplicates": 0, "anomalies": 0}
    s = SessionLocal()
    try:
        for e in events:
            if store_pos(s, e):
                res["accepted"] += 1
                hub.counts["tickets"] += (e.event_type.value == "TICKET_FIRE")
                _apply_signals(route_pos(e), {"pos_event": e.event_id})
                for a in r.on_pos(e):
                    store_anomaly(s, a)
                    await hub.publish("anomaly", _anomaly_dict(a))
                    res["anomalies"] += 1
            else:
                res["duplicates"] += 1
        s.commit()
    finally:
        s.close()
    for e in events:
        await hub.publish("pos_event", e.model_dump(mode="json"))
    return res


@app.post("/ingest/vision")
async def ingest_vision(events: list[VisionEvent]):
    r: Reconciler = state["reconciler"]
    scene: SceneConfig = state["scene"]
    zone_kinds = scene.cameras[0].zone_kinds() if scene.cameras else {}
    res = {"accepted": 0, "duplicates": 0, "anomalies": 0}
    s = SessionLocal()
    try:
        for e in events:
            if store_vision(s, e):
                res["accepted"] += 1
                hub.counts["plates_out"] += (
                    e.event_type.value == "OBJECT_CROSSED" and e.direction == "out")
                _apply_signals(route_vision(e, zone_kinds), {"vision_event": e.event_id})
                for a in r.on_vision(e):
                    store_anomaly(s, a)
                    await hub.publish("anomaly", _anomaly_dict(a))
                    res["anomalies"] += 1
            else:
                res["duplicates"] += 1
        s.commit()
    finally:
        s.close()
    for e in events:
        await hub.publish("vision_event", e.model_dump(mode="json"))
    return res


# ---------------------------------------------------------------- sorgular
@app.get("/anomalies")
async def get_anomalies(kind: str | None = Query(None),
                        include_suppressed: bool = Query(False),
                        limit: int = Query(200, le=1000)):
    s = SessionLocal()
    try:
        q = s.query(AnomalyRow).order_by(AnomalyRow.occurred_at_ms.desc()).limit(limit)
        rows = q.all()
        if kind:
            rows = [x for x in rows if x.kind == kind]
        if not include_suppressed:
            rows = [x for x in rows if not x.suppressed]
        return [_anomaly_dict(x) for x in rows]
    finally:
        s.close()


@app.get("/state")
async def get_state():
    actors = {}
    for name, sm in ACTORS.items():
        actors[name] = [
            {"id": a.actor_id, "state": a.state, "since_ms": a.since_ms}
            for a in sm.actors.values()]
    return {"actors": actors, "counts": hub.counts,
            "calibrating": state["reconciler"].calibrating,
            "zone_to_table": state["zone_to_table"]}


@app.get("/events/recent")
async def recent(limit: int = Query(100, le=300)):
    return list(hub.recent)[-limit:]


@app.get("/scene")
async def get_scene():
    return state["scene"].model_dump(mode="json")


@app.put("/scene")
async def put_scene(payload: dict):
    try:
        scene = SceneConfig.model_validate(payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(422, str(exc)) from exc
    SCENE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    state["scene"] = scene
    state["zone_to_table"] = {
        z.zone_id: z.pos_table_id
        for cam in scene.cameras for z in cam.zones
        if z.kind == "table" and z.pos_table_id}
    await hub.publish("scene_updated", {})
    return {"ok": True}


@app.get("/health")
async def health():
    return {"ok": True, "uptime_s": int(time.time() - START_TS)}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await hub.join(ws)
    try:
        while True:
            await ws.receive_text()  # ping
    except WebSocketDisconnect:
        hub.leave(ws)
