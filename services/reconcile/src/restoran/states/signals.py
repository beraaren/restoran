"""Event -> sinyal router'ı.

PosEvent ve VisionEvent akışını tek bir normalize sinyal stream'ine çevirir;
durum makineleri sadece sinyal bilir. entity_id çözümlemesi burada yapılır.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..contracts.events import PosEvent, PosEventType, VisionEvent, VisionEventType


@dataclass(frozen=True)
class Signal:
    actor_type: str          # plate | table | customer | chef | waiter
    actor_id: str
    name: str                # actors.py geçiş tablolarındaki sinyal adları
    at_ms: int
    evidence: dict = field(default_factory=dict)


def route_pos(e: PosEvent) -> list[Signal]:
    out: list[Signal] = []
    if e.event_type == PosEventType.TABLE_OPEN and e.table_id:
        # masa referans döngüsü POS tarafından sürüklenir; ticket/line sinyalleri
        # aşağıda table_id üzerinden masaya da yansır.
        pass
    if e.event_type == PosEventType.TICKET_FIRE:
        pid = e.line_id or e.item_id or f"{e.table_id}:{e.event_id}"
        out.append(Signal("plate", pid, "ticket_fired", e.occurred_at_ms,
                          {"pos": e.model_dump(mode="json")}))
        if e.table_id:
            out.append(Signal("table", e.table_id, "ticket_fired", e.occurred_at_ms,
                              {"pos": e.model_dump(mode="json")}))
        out.append(Signal("chef", "kitchen", "prep_started", e.occurred_at_ms,
                          {"pos": e.model_dump(mode="json")}))
    if e.event_type == PosEventType.ORDER_LINE_ADD and e.table_id:
        out.append(Signal("table", e.table_id, "customer_seated", e.occurred_at_ms,
                          {"pos": e.model_dump(mode="json")}))
    if e.event_type == PosEventType.PAYMENT and e.table_id:
        out.append(Signal("table", e.table_id, "table_clean", e.occurred_at_ms,
                          {"pos": e.model_dump(mode="json")}))
        out.append(Signal("customer", e.table_id, "paid", e.occurred_at_ms,
                          {"pos": e.model_dump(mode="json")}))
    if e.event_type == PosEventType.TABLE_CLOSE and e.table_id:
        out.append(Signal("table", e.table_id, "table_clean", e.occurred_at_ms,
                          {"pos": e.model_dump(mode="json")}))
    return out


# Vision zone kind -> ürettiği sinyal adı
_ZONE_KIND_SIGNAL_PLATE = {
    "pass_out": "left_kitchen",     # PASS çizgisi, mutfaktan çıkış yönü
    "prep": "prep_detected",        # hazırlık tezgâhı bölgesi
    "table": "served",              # masa poligonuna tabak girdi
    "wash": "cleared",              # bulaşık/atık bölgesi — tabak kalktı
}


def route_vision(e: VisionEvent, zone_kinds: dict[str, str]) -> list[Signal]:
    """zone_kinds: zone_id -> kind (pass_out/prep/table/wash/...)"""
    out: list[Signal] = []
    if e.object_class in ("plate", "bowl", "cup", "glass", "tray"):
        pid = f"trk-{e.camera_id}-{e.track_id}"
        if e.event_type == VisionEventType.OBJECT_CROSSED and e.zone_id:
            kind = zone_kinds.get(e.zone_id)
            if kind == "pass_out" and e.direction == "out":
                out.append(Signal("plate", pid, "left_kitchen", e.occurred_at_ms,
                                  {"vision": e.model_dump(mode="json")}))
        if e.event_type == VisionEventType.OBJECT_ENTERED and e.zone_id:
            kind = zone_kinds.get(e.zone_id)
            sig = _ZONE_KIND_SIGNAL_PLATE.get(kind or "")
            if sig == "served":
                out.append(Signal("plate", pid, "served", e.occurred_at_ms,
                                  {"vision": e.model_dump(mode="json"), "table_zone": e.zone_id}))
                out.append(Signal("table", e.zone_id, "served", e.occurred_at_ms,
                                  {"vision": e.model_dump(mode="json")}))
            elif sig:
                out.append(Signal("plate", pid, sig, e.occurred_at_ms,
                                  {"vision": e.model_dump(mode="json")}))
    if e.object_class == "person" and e.event_type == VisionEventType.OBJECT_ENTERED:
        kind = zone_kinds.get(e.zone_id or "", "")
        if kind == "table":
            out.append(Signal("customer", e.zone_id or "unknown", "seated",
                              e.occurred_at_ms, {"vision": e.model_dump(mode="json")}))
            out.append(Signal("table", e.zone_id, "customer_seated", e.occurred_at_ms,
                              {"vision": e.model_dump(mode="json")}))
    return out
