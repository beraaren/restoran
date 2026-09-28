"""Mock POS — Ingestion Contract'a tam uyan sahte kasa programı.

Demo senaryoları:
  normal   : TABLE_OPEN -> ORDER_LINE_ADD -> TICKET_FIRE -> (PAYMENT -> TABLE_CLOSE)
  kayit_disi: latte üretilir ama ticket YOK (vision TICKETSIZ_URETIM üretmeli)
  iptal_tuzagi: TICKET_FIRE var, LINE_VOID var, üretim YOK (URETILMEYEN_SIPARIS)

Kullanım:
  python -m restoran.pos.mock --out data/pos_events.jsonl [--speed 8.0]
"""
from __future__ import annotations

import argparse
import json
import time
import uuid
from decimal import Decimal

from ..contracts.events import PosEvent, PosEventType


def _mk(t: float, etype: PosEventType, **kw) -> PosEvent:
    """t = servis başlangıcından saniye cinsinden offset."""
    return PosEvent(
        event_id=str(uuid.uuid4()), event_type=etype,
        occurred_at_ms=int(t * 1000), **kw)


def build_scenario(now_wall_ms: int) -> list[PosEvent]:
    e: list[PosEvent] = []

    # --- Masa 1: normal servis (2 ürün) ---
    e += [
        _mk(5, PosEventType.TABLE_OPEN, table_id="M1"),
        _mk(30, PosEventType.ORDER_LINE_ADD, table_id="M1", line_id="L1",
             item_id="kofte", item_name="Porsiyon Köfte", amount_tl=Decimal("180")),
        _mk(31, PosEventType.ORDER_LINE_ADD, table_id="M1", line_id="L2",
             item_id="salata", item_name="Mevsim Salata", amount_tl=Decimal("70")),
        _mk(33, PosEventType.TICKET_FIRE, table_id="M1", line_id="L1",
             item_id="kofte", item_name="Porsiyon Köfte", amount_tl=Decimal("180")),
        _mk(34, PosEventType.TICKET_FIRE, table_id="M1", line_id="L2",
             item_id="salata", item_name="Mevsim Salata", amount_tl=Decimal("70")),
        _mk(240, PosEventType.PAYMENT, table_id="M1", amount_tl=Decimal("250")),
        _mk(245, PosEventType.TABLE_CLOSE, table_id="M1"),
    ]
    # --- Masa 2: kayıt dışı latte — ticket YOK (kasaya da girmez) ---
    e += [
        _mk(20, PosEventType.TABLE_OPEN, table_id="M2"),
        _mk(40, PosEventType.ORDER_LINE_ADD, table_id="M2", line_id="L3",
             item_id="su", item_name="Su", amount_tl=Decimal("25")),
        _mk(41, PosEventType.TICKET_FIRE, table_id="M2", line_id="L3",
             item_id="su", item_name="Su", amount_tl=Decimal("25")),
    ]
    # --- Masa 3: iptal tuzağı — fire edildi, void edildi, üretim yok ---
    e += [
        _mk(60, PosEventType.TABLE_OPEN, table_id="M3"),
        _mk(90, PosEventType.ORDER_LINE_ADD, table_id="M3", line_id="L4",
             item_id="steak", item_name="Antrikot", amount_tl=Decimal("420")),
        _mk(91, PosEventType.TICKET_FIRE, table_id="M3", line_id="L4",
             item_id="steak", item_name="Antrikot", amount_tl=Decimal("420")),
        _mk(160, PosEventType.LINE_VOID, table_id="M3", line_id="L4",
            item_id="steak", item_name="Antrikot", amount_tl=Decimal("420")),
        _mk(300, PosEventType.PAYMENT, table_id="M3", amount_tl=Decimal("0")),
        _mk(305, PosEventType.TABLE_CLOSE, table_id="M3"),
    ]
    # --- Masa 4: ödeme kaçışı (yendi, kalktı, payment yok) ---
    e += [
        _mk(100, PosEventType.TABLE_OPEN, table_id="M4"),
        _mk(120, PosEventType.ORDER_LINE_ADD, table_id="M4", line_id="L5",
             item_id="iskender", item_name="İskender", amount_tl=Decimal("260")),
        _mk(121, PosEventType.TICKET_FIRE, table_id="M4", line_id="L5",
             item_id="iskender", item_name="İskender", amount_tl=Decimal("260")),
    ]
    # absolute -> wall clock
    for ev in e:
        ev.occurred_at_ms += now_wall_ms
        ev.venue_id = "demo"
        ev.source = "mock-pos"
    return e


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("data/pos_events.jsonl"))
    ap.add_argument("--speed", type=float, default=0.0,
                    help="0 = hepsini hemen yaz; >0 = gerçek zamanlı akış (hız çarpanı)")
    ap.add_argument("--http", default=None,
                    help="POST bu URL'ye (örn. http://localhost:8000/ingest/pos) — JSONL yerine")
    args = ap.parse_args()

    import sys
    from pathlib import Path

    events = build_scenario(int(time.time() * 1000))
    if args.http:
        import httpx
        if args.speed > 0:
            base = events[0].occurred_at_ms
            prev = 0.0
            for ev in events:
                delta = (ev.occurred_at_ms - base - prev) / 1000 / args.speed
                time.sleep(max(delta, 0))
                prev = ev.occurred_at_ms - base
                httpx.post(args.http, json=ev.model_dump(mode="json"), timeout=5)
        else:
            httpx.post(args.http, json=[ev.model_dump(mode="json") for ev in events],
                       timeout=10)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w") as f:
            for ev in events:
                f.write(ev.model_dump_json() + "\n")
    print(f"{len(events)} POS event üretildi -> "
          f"{args.http or args.out}")


if __name__ == "__main__":
    main()
