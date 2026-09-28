"""Uçtan uca iskelet testi — video/CUDA gerektirmez.

Senaryo (config/scene.demo.json ile aynı masa isimleri):
  1) M1: ticket fire + PASS çıkışı        -> anomali YOK
  2) M2: ticket fire YOK, PASS çıkışı     -> TICKETSIZ_URETIM
  3) M3: ticket fire + PASS çıkışı YOK    -> URETILMEYEN_SIPARIS
  4) M4 person seated + TABLE_OPEN yok    -> ACILMAMIS_MASA
Ayrıca idempotency (aynı event_id iki kez store_pos) test edilir.

Çalıştırma: .venv/bin/python tests/smoke_reconcile.py
"""
from __future__ import annotations

import sys
import uuid
from decimal import Decimal

sys.path.insert(0, "src")

from restoran.contracts.events import PosEvent, PosEventType, VisionEvent, VisionEventType
from restoran.reconcile.engine import Reconciler, RuleWindows
from restoran.store.db import init_db, store_pos, SessionLocal, PosEventRow

T0 = 1_000_000_000_000  # sabit epoch; test deterministik kalsın


def pos(t_s: float, etype: PosEventType, **kw) -> PosEvent:
    return PosEvent(event_id=str(uuid.uuid4()), event_type=etype,
                    occurred_at_ms=T0 + int(t_s * 1000), **kw)


def vision(t_s: float, etype: VisionEventType, cls: str, zone: str | None,
           direction: str | None, tid: int) -> VisionEvent:
    return VisionEvent(event_id=str(uuid.uuid4()), event_type=etype,
                       occurred_at_ms=T0 + int(t_s * 1000), camera_id="cam0",
                       track_id=tid, object_class=cls, zone_id=zone,
                       direction=direction, confidence=0.9)


def main() -> None:
    r = Reconciler(RuleWindows(ticket_to_plate_s=180, plate_to_ticket_s=120,
                               seating_without_open_s=300))

    anomalies = []
    # 1) M1 normal: ORDER + 2 ticket
    anomalies += r.on_pos(pos(0, PosEventType.TABLE_OPEN, table_id="M1"))
    anomalies += r.on_pos(pos(10, PosEventType.ORDER_LINE_ADD, table_id="M1",
                              line_id="L1", item_id="kofte", item_name="Köfte",
                              amount_tl=Decimal("180")))
    tk1 = pos(11, PosEventType.TICKET_FIRE, table_id="M1", line_id="L1",
              item_id="kofte", item_name="Köfte", amount_tl=Decimal("180"))
    anomalies += r.on_pos(tk1)
    # tabak 40. saniyede PASS'tan çıkar -> eşleşmeli
    anomalies += r.on_vision(vision(40, VisionEventType.OBJECT_CROSSED, "plate",
                                    "pass-out", "out", 101))

    # 2) M2 kayıt dışı latte: ticket yok, PASS çıkışı var
    anomalies += r.on_vision(vision(80, VisionEventType.OBJECT_CROSSED, "cup",
                                    "pass-out", "out", 102))

    # 3) M3 hayalet sipariş: ticket var, PASS çıkışı hiç yok
    anomalies += r.on_pos(pos(60, PosEventType.TABLE_OPEN, table_id="M3"))
    anomalies += r.on_pos(pos(90, PosEventType.TICKET_FIRE, table_id="M3",
                              line_id="L9", item_id="steak", item_name="Antrikot",
                              amount_tl=Decimal("420")))

    # 4) M4 kişi oturdu, POS açılmadı
    anomalies += r.on_vision(vision(100, VisionEventType.OBJECT_ENTERED, "person",
                                    "table-m4", None, 500))

    # pencere dolması: now = T0 + 600s
    anomalies += r.evaluate(T0 + 600_000, {"table-m4": "M4"})

    kinds = sorted(a.kind for a in anomalies if not a.suppressed)
    print("üretilen anomaller:", kinds)
    assert "TICKETSIZ_URETIM" in kinds, "kayıt dışı üretim kaçtı"
    assert "URETILMEYEN_SIPARIS" in kinds, "hayalet sipariş kaçtı"
    assert "ACILMAMIS_MASA" in kinds, "açılmamış masa kaçtı"
    assert kinds.count("TICKETSIZ_URETIM") == 1, "M1'deki normal tabak da sayıldı!"
    assert sum(1 for k in kinds if k == "URETILMEYEN_SIPARIS") == 1

    # idempotency: aynı event_id iki kez
    init_db()
    s = SessionLocal()
    try:
        assert store_pos(s, tk1) is True
        s.commit()
        assert store_pos(s, tk1) is False, "duplicate yakalanmadı"
    finally:
        s.close()

    print("SMOKE OK — 3 anomali tipi doğru, normal eşleşme anomali üretmedi, idempotency çalışıyor")


if __name__ == "__main__":
    main()
