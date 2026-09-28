"""Zone (bölge) config şeması.

Kamera görüntüsü üzerinde elle çizilen poligonlar/çizgiler JSON'da tutulur.
Kamera değişirse sadece bu config güncellenir — model eğitimi gerekmez.
Koordinatlar normalized (0..1) tutulur; böylece çözünürlük değişse de kaymaz.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

ZoneKind = Literal["pass_out", "pass_in", "prep", "table", "wash", "entrance",
                   "pos_terminal", "staff_area", "waiting_area"]


class Point(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class Zone(BaseModel):
    zone_id: str
    kind: ZoneKind
    label: str = ""                      # panelde görünen ad ("Masa 3")
    polygon: list[Point] = Field(min_length=3)
    pos_table_id: str | None = None      # kind == "table" için POS masa eşleşmesi
    min_dwell_ms: int = 400              # histeresis: bölgede kalma eşiği
    enabled: bool = True


class PassLine(BaseModel):
    """PASS noktası: iki uçlu çizgi + geçiş yönü. Mutfak çıkışı 'boğaz noktası'."""

    zone_id: str
    kind: ZoneKind = "pass_out"
    label: str = "Mutfak çıkışı"
    a: Point
    b: Point
    # direction "out": a->b tarafı mutfak, diğer taraf salon (centroid hangi tarafa
    # geçiş yapıyorsa out/in olarak raporlanır)
    min_dwell_ms: int = 0
    enabled: bool = True


class CameraConfig(BaseModel):
    camera_id: str = "cam0"
    label: str = "Ana kamera"
    resolution: tuple[int, int] = (1280, 720)
    fps: float = 25.0
    zones: list[Zone] = Field(default_factory=list)
    pass_lines: list[PassLine] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_ids(self) -> "CameraConfig":
        ids = [z.zone_id for z in self.zones] + [p.zone_id for p in self.pass_lines]
        if len(ids) != len(set(ids)):
            raise ValueError("zone_id'ler benzersiz olmalı")
        return self

    def zone_kinds(self) -> dict[str, str]:
        """signals.route_vision için zone_id -> kind haritası."""
        m = {z.zone_id: z.kind for z in self.zones}
        m.update({p.zone_id: p.kind for p in self.pass_lines})
        return m

    def table_zone_to_pos(self) -> dict[str, str]:
        return {z.zone_id: z.pos_table_id
                for z in self.zones if z.kind == "table" and z.pos_table_id}


class SceneConfig(BaseModel):
    """Bir demo/saha kurulumu: bir veya daha fazla kamera."""

    venue_id: str = "default"
    cameras: list[CameraConfig] = Field(default_factory=list)
