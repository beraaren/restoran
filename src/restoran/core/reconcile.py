"""Çaprazlama (mutabakat) motoru — Vision ↔ POS event uyuşmazlıkları.

Plan Bölüm 3. Kurallar zaman pencereli eşleştirme çalışır:
- left_kitchen (PASS 'out') var, geriye dönük pencerede TICKET_FIRE yok -> TICKETSIZ_URETIM
- TICKET_FIRE var, ileri pencerede hiç PASS çıkışı yok                  -> URETILMEYEN_SIPARIS
- kişi masa zone'unda oturuyor, POS'ta masa açılmamış (eşik süreyi aştı)-> ACILMAMIS_MASA

Eşleştirme consume temelli: bir ticket bir geçişle eşleşince ikisi de düşer,
çift anomali üretilmez. Kalibrasyon modunda anomaller `suppressed=True` işaretli
üretilir (panel gri gösterir, baz öğrenilir). Pencereler RuleWindows'tan config.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from ..contracts.events import PosEvent, PosEventType, VisionEvent


@dataclass
class Anomaly:
    anomaly_id: str
    kind: str                 # TICKETSIZ_URETIM | URETILMEYEN_SIPARIS | ACILMAMIS_MASA
    severity: str             # high | medium | low
    occurred_at_ms: int
    amount_tl: Decimal | None
    title: str
    detail: str
    table_id: str | None = None
    track_id: int | None = None
    evidence: dict = field(default_factory=dict)
    suppressed: bool = False  # kalibrasyon penceresinde


@dataclass
class RuleWindows:
    ticket_to_plate_s: int = 180      # TICKET_FIRE -> beklenen PASS çıkışı
    plate_to_ticket_s: int = 120      # PASS çıkışı -> geriye dönük ticket araması
    seating_without_open_s: int = 300 # seated -> TABLE_OPEN eşiği

    @classmethod
    def from_env(cls) -> "RuleWindows":
        import os
        d = {}
        for f in ("ticket_to_plate_s", "plate_to_ticket_s", "seating_without_open_s"):
            v = os.environ.get(f.upper())
            if v:
                d[f] = int(v)
        return cls(**d)


@dataclass
class _Plate:
    ev: VisionEvent
    matched: bool = False


@dataclass
class _Ticket:
    ev: PosEvent
    matched: bool = False


class Reconciler:
    """Stream tabanlı: event'ler geldikçe beslenir; evaluate() dolmuş pencereleri tarar."""

    def __init__(self, windows: RuleWindows | None = None, calibrating: bool = False):
        self.w = windows or RuleWindows()
        self.calibrating = calibrating
        self._plates: list[_Plate] = []
        self._tickets: list[_Ticket] = []
        self._person_seated: dict[str, int] = {}   # zone_id -> seated_at_ms
        self._opened_tables: set[str] = set()       # TABLE_OPEN veya sipariş görmüş masalar

    # ---------------------------------------------------------- POS girişi
    def on_pos(self, e: PosEvent) -> list[Anomaly]:
        if e.event_type == PosEventType.TICKET_FIRE:
            self._tickets.append(_Ticket(ev=e))
        if e.table_id and e.event_type in (
                PosEventType.TABLE_OPEN, PosEventType.ORDER_LINE_ADD,
                PosEventType.TICKET_FIRE):
            self._opened_tables.add(e.table_id)
        return []

    # ---------------------------------------------------------- Vision girişi
    def on_vision(self, e: VisionEvent) -> list[Anomaly]:
        out: list[Anomaly] = []
        if e.event_type.value == "OBJECT_CROSSED" and e.direction != "out":
            return out  # yalnizca mutfaktan salona cikislar uretim sayilir
        if (e.event_type.value == "OBJECT_CROSSED"
                and e.object_class in ("plate", "cup", "glass", "bottle", "tray")):
            out += self._on_plate_out(e)
        if e.object_class == "person" and e.event_type.value == "OBJECT_ENTERED" and e.zone_id:
            self._person_seated.setdefault(e.zone_id, e.occurred_at_ms)
        return out

    def _on_plate_out(self, e: VisionEvent) -> list[Anomaly]:
        """Geçen tabak: geriye dönük eşleşmemiş TICKET_FIRE ara."""
        lo = e.occurred_at_ms - self.w.plate_to_ticket_s * 1000
        cand = [t for t in self._tickets
                if not t.matched and lo <= t.ev.occurred_at_ms <= e.occurred_at_ms]
        p = _Plate(ev=e)
        self._plates.append(p)
        if cand:
            t = max(cand, key=lambda t: t.ev.occurred_at_ms)  # en yakın (taze) ticket
            t.matched = True
            p.matched = True
            return []
        return [self._mk(
            "TICKETSIZ_URETIM", "high", e.occurred_at_ms, None,
            f"Kayıt dışı üretim: {e.object_class} mutfaktan çıktı, adisyonda karşılığı yok",
            f"track#{e.track_id} "
            f"{datetime.fromtimestamp(e.occurred_at_ms / 1000, timezone.utc):%H:%M:%S} "
            f"PASS'tan geçti; geriye dönük {self.w.plate_to_ticket_s}s içinde "
            "eşleşen TICKET_FIRE yok.",
            track_id=e.track_id,
            evidence={"vision": e.model_dump(mode="json")})]

    # ---------------------------------------------------------- Periyodik değerlendirme
    def evaluate(self, now_ms: int,
                 zone_to_table: dict[str, str] | None = None) -> list[Anomaly]:
        """Runner ~30s'de bir çağırır; süresi dolmuş pencereleri değerlendirir."""
        out: list[Anomaly] = []
        zt = zone_to_table or {}

        # 1) HAYALET SİPARİŞ: ticket fire oldu, ileri pencere doldu, PASS çıkışı yok
        keep: list[_Ticket] = []
        for t in self._tickets:
            deadline = t.ev.occurred_at_ms + self.w.ticket_to_plate_s * 1000
            if now_ms < deadline:
                keep.append(t)
                continue
            if t.matched:
                continue  # bitti
            produced = any(pl.matched and
                           t.ev.occurred_at_ms <= pl.ev.occurred_at_ms <= deadline
                           for pl in self._plates)
            if not produced:
                out.append(self._mk(
                    "URETILMEYEN_SIPARIS", "high", t.ev.occurred_at_ms,
                    t.ev.amount_tl,
                    f"Hayalet sipariş: {t.ev.item_name or t.ev.item_id or '?'} "
                    "fire edildi ama üretim yok",
                    f"TICKET_FIRE "
                    f"{datetime.fromtimestamp(t.ev.occurred_at_ms / 1000, timezone.utc):%H:%M:%S}"
                    f" — {self.w.ticket_to_plate_s}s içinde PASS'tan ürün geçmedi. "
                    "İptal tuzağı / kayıtsız consumption şüphesi.",
                    table_id=t.ev.table_id,
                    evidence={"pos": t.ev.model_dump(mode="json")}))
        self._tickets = keep

        # 2) AÇILMAMIŞ MASA: kişi oturdu, eşik süre geçti, POS'ta masa açılmadı
        for zone_id, seated_at in list(self._person_seated.items()):
            table = zt.get(zone_id)
            if not table:
                continue
            if now_ms - seated_at > self.w.seating_without_open_s * 1000:
                if table not in self._opened_tables:
                    out.append(self._mk(
                        "ACILMAMIS_MASA", "medium", seated_at, None,
                        f"Masa {table} dolu ama adisyon açılmamış",
                        f"{self.w.seating_without_open_s}s geçti, TABLE_OPEN/ORDER_LINE_ADD yok.",
                        table_id=table, evidence={"seated_at_ms": seated_at}))
                del self._person_seated[zone_id]
        return out

    # ---------------------------------------------------------- yardimci
    def _mk(self, kind, sev, at, amount, title, detail, table_id=None,
            track_id=None, evidence=None) -> Anomaly:
        return Anomaly(anomaly_id=str(uuid.uuid4()), kind=kind, severity=sev,
                       occurred_at_ms=at, amount_tl=amount, title=title,
                       detail=detail, table_id=table_id, track_id=track_id,
                       evidence=evidence or {}, suppressed=self.calibrating)
