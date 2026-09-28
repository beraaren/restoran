"""Ingestion Contract v1 — POS ve Vision event şemaları.

Kural: POS adaptörleri bize uyar; uymayan POS ile çalışmayız.
- Tüm timestamp'ler UTC毫秒 (int epoch ms). Tek zaman kaynağı.
- Her event idempotent: (camera_id|venue_id, event_id) tekrar gönderilirse yok sayılır.
- Para Decimal, kanonik birim payload içinde düz metin alanı olarak.
"""
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PosEventType(str, Enum):
    """Minimum Viable Event Set — POS adaptörünün desteklemek ZORUNDA olduğu olaylar."""

    TABLE_OPEN = "TABLE_OPEN"        # masa açıldı (adisyon başladı)
    ORDER_LINE_ADD = "ORDER_LINE_ADD" # adisyona satır eklendi
    TICKET_FIRE = "TICKET_FIRE"       # satır mutfağa gönderildi (üretim emri)
    LINE_VOID = "LINE_VOID"           # satır iptal (ZORUNLU — Without this, ghost sales are invisible)
    PAYMENT = "PAYMENT"               # ödeme alındı
    TABLE_CLOSE = "TABLE_CLOSE"       # adisyon kapandı


class VisionEventType(str, Enum):
    """Vision pipeline'ın ürettiği fiziksel gerçeklik olayları (Zone tabanlı)."""

    OBJECT_CROSSED = "OBJECT_CROSSED"   # takip edilen nesne bir çizgiyi/poligon kenarını geçti
    OBJECT_ENTERED = "OBJECT_ENTERED"   # nesne bir zone'a girdi
    OBJECT_EXITED = "OBJECT_EXITED"     # nesne bir zone'dan çıktı
    OBJECT_PRESENT = "OBJECT_PRESENT"   # nesne zone içinde kaldı (histeresis teyidi)


class PosEvent(BaseModel):
    event_id: str = Field(min_length=1, description="Idempotency key — adaptör üretir, tekrarlarında aynı olmalı")
    event_type: PosEventType
    occurred_at_ms: int = Field(gt=0, description="UTC epoch milliseconds")
    venue_id: str = "default"
    table_id: str | None = None
    ticket_id: str | None = None
    line_id: str | None = None
    item_id: str | None = None
    item_name: str | None = None
    qty: Decimal = Decimal("1")
    unit: str | None = Field(default=None, description="kanonik birim: gram | ml | adet")
    amount_tl: Decimal | None = None
    staff_id: str | None = None
    source: str = "mock"
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("amount_tl")
    @classmethod
    def _amount_nonneg(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v < 0:
            raise ValueError("amount_tl negatif olamaz (iptal için LINE_VOID kullan)")
        return v


class VisionEvent(BaseModel):
    event_id: str = Field(min_length=1)
    event_type: VisionEventType
    occurred_at_ms: int = Field(gt=0)
    venue_id: str = "default"
    camera_id: str = "cam0"
    track_id: int | None = None
    object_class: str = Field(description="plate | bowl | cup | glass | tray | person ...")
    zone_id: str | None = None
    direction: str | None = Field(default=None, description="crossed çizgilerde: in | out")
    confidence: float = Field(ge=0, le=1)
    frame_idx: int | None = None
    bbox: tuple[float, float, float, float] | None = Field(
        default=None, description="x1,y1,x2,y2 (piksel)"
    )
    video_path: str | None = None
    source: str = "vision"
    payload: dict[str, Any] = Field(default_factory=dict)


class IngestResult(BaseModel):
    accepted: int = 0
    duplicates: int = 0
    rejected: list[str] = Field(default_factory=list)
