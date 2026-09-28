"""Event store — Postgres (dev'de SQLite fallback).

idempotency: (source, event_id) unique. Anomalılar ayrı tabloda.
Para NUMERIC; timestamp UTC-ms BIGINT (canon: tek zaman kaynağı).
"""
from __future__ import annotations

import os
from decimal import Decimal

from sqlalchemy import (JSON, BigInteger, Boolean, Column, DateTime, Index,
                        Numeric, String, Text, create_engine)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from ..contracts.events import PosEvent, VisionEvent
from ..core.reconcile import Anomaly

Base = declarative_base()

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///restoran.db")


class PosEventRow(Base):
    __tablename__ = "pos_events"
    event_id = Column(String, primary_key=True)
    event_type = Column(String, nullable=False, index=True)
    occurred_at_ms = Column(BigInteger, nullable=False, index=True)
    venue_id = Column(String, default="default")
    table_id = Column(String, nullable=True)
    ticket_id = Column(String, nullable=True)
    line_id = Column(String, nullable=True)
    item_id = Column(String, nullable=True)
    item_name = Column(String, nullable=True)
    qty = Column(Numeric(12, 3), nullable=True)
    unit = Column(String, nullable=True)
    amount_tl = Column(Numeric(12, 2), nullable=True)
    staff_id = Column(String, nullable=True)
    source = Column(String, default="mock")
    payload = Column(JSON, default=dict)
    ingested_at = Column(DateTime, nullable=False)


class VisionEventRow(Base):
    __tablename__ = "vision_events"
    event_id = Column(String, primary_key=True)
    event_type = Column(String, nullable=False, index=True)
    occurred_at_ms = Column(BigInteger, nullable=False, index=True)
    venue_id = Column(String, default="default")
    camera_id = Column(String, nullable=False)
    track_id = Column(BigInteger, nullable=True)
    object_class = Column(String, nullable=False, index=True)
    zone_id = Column(String, nullable=True)
    direction = Column(String, nullable=True)
    confidence = Column(BigInteger, nullable=True)  # float*1e6 saklanır
    frame_idx = Column(BigInteger, nullable=True)
    bbox = Column(JSON, nullable=True)
    video_path = Column(String, nullable=True)
    source = Column(String, default="vision")
    payload = Column(JSON, default=dict)
    ingested_at = Column(DateTime, nullable=False)


class AnomalyRow(Base):
    __tablename__ = "anomalies"
    anomaly_id = Column(String, primary_key=True)
    kind = Column(String, nullable=False, index=True)
    severity = Column(String, nullable=False)
    occurred_at_ms = Column(BigInteger, nullable=False, index=True)
    amount_tl = Column(Numeric(12, 2), nullable=True)
    title = Column(String, nullable=False)
    detail = Column(Text, nullable=False)
    table_id = Column(String, nullable=True)
    track_id = Column(BigInteger, nullable=True)
    evidence = Column(JSON, default=dict)
    suppressed = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False)


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def init_db() -> None:
    Base.metadata.create_all(engine)


def _now_utc_dt():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).replace(tzinfo=None)


def store_pos(s: Session, e: PosEvent) -> bool:
    """True ise yeni kaydedildi, False ise duplicate."""
    if s.get(PosEventRow, e.event_id):
        return False
    s.add(PosEventRow(
        event_id=e.event_id, event_type=e.event_type.value,
        occurred_at_ms=e.occurred_at_ms, venue_id=e.venue_id, table_id=e.table_id,
        ticket_id=e.ticket_id, line_id=e.line_id, item_id=e.item_id,
        item_name=e.item_name, qty=e.qty, unit=e.unit, amount_tl=e.amount_tl,
        staff_id=e.staff_id, source=e.source, payload=e.payload,
        ingested_at=_now_utc_dt()))
    return True


def store_vision(s: Session, e: VisionEvent) -> bool:
    if s.get(VisionEventRow, e.event_id):
        return False
    s.add(VisionEventRow(
        event_id=e.event_id, event_type=e.event_type.value,
        occurred_at_ms=e.occurred_at_ms, venue_id=e.venue_id, camera_id=e.camera_id,
        track_id=e.track_id, object_class=e.object_class, zone_id=e.zone_id,
        direction=e.direction, confidence=int(e.confidence * 1e6),
        frame_idx=e.frame_idx, bbox=list(e.bbox) if e.bbox else None,
        video_path=e.video_path, source=e.source, payload=e.payload,
        ingested_at=_now_utc_dt()))
    return True


def store_anomaly(s: Session, a: Anomaly) -> None:
    if s.get(AnomalyRow, a.anomaly_id):
        return
    s.add(AnomalyRow(
        anomaly_id=a.anomaly_id, kind=a.kind, severity=a.severity,
        occurred_at_ms=a.occurred_at_ms, amount_tl=a.amount_tl, title=a.title,
        detail=a.detail, table_id=a.table_id, track_id=a.track_id,
        evidence=a.evidence, suppressed=a.suppressed, created_at=_now_utc_dt()))
