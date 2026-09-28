"""UC-UCA DEMO — tek komut: .venv/bin/python tools/demo.py

Akis:
  1) API sunucusu baslar (:8100, taze SQLite, kisa demo pencereleri)
  2) Vision stream'i T0 tabaninda baslar (video x2 hizinda API'ye akar;
     3 kisi/crop PASS cizgisini ~5sn / 14sn / 22sn civarinde keser)
  3) POS senaryosu T0 ile ayni tabana gore enjekte edilir:
     - M1: ticket T0+0.3sn -> 5sn'deki gecisle ESLESIR (normal servis)
     - M2: ticket T0     -> hicbir gecisle eslesmez -> URETILMEYEN_SIPARIS
     - 14sn ve 22sn gecisleri ticketsiz -> TICKETSIZ_URETIM x2
  4) Ozet basilir; API arka planda calismaya devam eder

Panel icin ayri terminal: cd web && npm run dev -> http://localhost:5173
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from decimal import Decimal
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from restoran.contracts.events import PosEvent, PosEventType  # noqa: E402

API = "http://127.0.0.1:8100"


def pos(t_s: float, base_ms: int, etype: PosEventType, **kw) -> PosEvent:
    return PosEvent(event_id=str(uuid.uuid4()), event_type=etype,
                    occurred_at_ms=base_ms + int(t_s * 1000), venue_id="demo",
                    source="mock-pos", **kw)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--speed", type=float, default=2.0,
                    help="video akis hiz carpani (2 = 2x)")
    ap.add_argument("--gpu", action="store_true", help="vision icin CUDA kullan")
    args = ap.parse_args()

    db = ROOT / "data/restoran.db"
    if db.exists():
        db.unlink()
    log = open(ROOT / "logs/api.log", "w")
    env = {**{k: v for k, v in os.environ.items() if k in ("PATH", "HOME")},
           "DATABASE_URL": f"sqlite:///{db}",
           "SCENE_PATH": str(ROOT / "config/scene.passpeople.json"),
           "TICKET_TO_PLATE_S": "6", "PLATE_TO_TICKET_S": "10",
           "SEATING_WITHOUT_OPEN_S": "5"}
    proc = subprocess.Popen(
        [str(ROOT / ".venv/bin/python"), "-m", "uvicorn", "restoran.api.main:app",
         "--port", "8100"], cwd=ROOT, env=env, stdout=log, stderr=log)
    print("* API baslatiliyor (:8100)...")
    t0 = time.time()
    while time.time() - t0 < 30:
        if proc.poll() is not None:
            raise SystemExit("API coktu -> logs/api.log")
        try:
            if httpx.get(f"{API}/health", timeout=2).status_code == 200:
                break
        except Exception:
            time.sleep(0.3)
    else:
        raise SystemExit("API baslamadi -> logs/api.log")

    # Vision stream baslamadan hemen once ortak T0
    base_ms = int(time.time() * 1000) + 2000  # 2sn runner startup payi
    print("* Vision stream baslatiliyor (x%.1f, T0 = %d)" % (args.speed, base_ms))
    vproc = subprocess.Popen(
        [str(ROOT / ".venv/bin/python"), "-m", "restoran.vision.runner",
         str(ROOT / "data/pass_people.mp4"),
         "--scene", str(ROOT / "config/scene.passpeople.json"),
         "--out", str(ROOT / "data/vision_events.jsonl"),
         "--start-ms", str(base_ms), "--http", f"{API}/ingest/vision",
         "--stream", "--speed", str(args.speed), "--force-class", "plate"],
        cwd=ROOT, env={**env, "CUDA_VISIBLE_DEVICES": "" if not args.gpu else "0"})
    time.sleep(1.0)

    # crossing'ler ~5/14/22. sn'de. Ticket'lar GECON Kalirsa eslesen ticket
    # kaymasi olur (en taze ticket tuketir); bu yuzden M2 hayalet ticket'i
    # tum gecisler bittikten sonra atilir -> geriye donuk pencerede ticket
    # bulamayan gecisler TICKETSIZ_URETIM, ticket'in kendi penceresi bos
    # kalacagi icin URETILMEYEN_SIPARIS dogar.
    speed = args.speed
    c1 = 5.0 / speed; c2 = 14.0 / speed; c3 = 22.0 / speed   # video sn -> stream sn
    events = [
        pos(0.0, base_ms, PosEventType.TABLE_OPEN, table_id="M1"),
        pos(max(c1 - 0.5, 0.2), base_ms, PosEventType.ORDER_LINE_ADD, table_id="M1",
            line_id="L1", item_id="kofte", item_name="Porsiyon Köfte",
            amount_tl=Decimal("180")),
        pos(max(c1 - 0.3, 0.3), base_ms, PosEventType.TICKET_FIRE, table_id="M1",
            line_id="L1", item_id="kofte", item_name="Porsiyon Köfte",
            amount_tl=Decimal("180")),
        pos(c3 + 0.5, base_ms, PosEventType.TABLE_OPEN, table_id="M2"),
        pos(c3 + 0.7, base_ms, PosEventType.TICKET_FIRE, table_id="M2", line_id="L2",
            item_id="steak", item_name="Antrikot", amount_tl=Decimal("420")),
    ]
    r = httpx.post(f"{API}/ingest/pos",
                   json=[e.model_dump(mode="json") for e in events], timeout=10)
    print(f"* POS enjekte edildi: {r.json()}")

    vproc.wait()
    # hayalet ticket degerlendirmesi: M2 fire + ticket_to_plate (6sn) + buffer
    wait_s = c3 + 0.7 + 6 + 8
    print(f"* ~{wait_s:.0f} sn bekleniyor (pencereler + periyodik degerlendirme)...")
    time.sleep(wait_s)

    an = httpx.get(f"{API}/anomalies", timeout=5).json()
    st = httpx.get(f"{API}/state", timeout=5).json()
    print("\n=== DEMO SONUCU ===")
    print(f"PASS gecisi: {st['counts']['plates_out']} | fire: {st['counts']['tickets']}")
    print(f"anomali: {len(an)}")
    for a in an:
        print(f"  [{a['severity'].upper():6}] {a['kind']:22} {a['title']}")
    print("\nPanel icin ayri terminal:  cd web && npm run dev  -> http://localhost:5173")
    print(f"API arka planda calisiyor (pid {proc.pid}). Durdurmak: kill {proc.pid}")


if __name__ == "__main__":
    main()
