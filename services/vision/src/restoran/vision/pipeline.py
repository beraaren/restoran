"""Vision pipeline v0 — video -> VisionEvent akışı.

Akış: YOLO tespit + ByteTrack takibi -> centroid -> PASS çizgisi geçiş / zone giriş
histeresis + grace filtresi. Kamera canlı değilken video dosyası üzerinden çalışır.

v1'de COCO önceden eğitilmiş sınıfları kullanılır (yemek sınıflandırması YOK,
sayım var): bowl/cup/wine_glass/bottle -> ürün; person -> kişi.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import cv2

from ..config.geometry import bbox_center, point_in_polygon, side_of_line
from ..config.zones import CameraConfig, PassLine, Zone
from ..contracts.events import VisionEvent, VisionEventType

# COCO sınıf -> bizim kanonik ürün sınıfımız
COCO_TO_OBJECT = {
    "bowl": "plate",
    "cup": "cup",
    "wine glass": "glass",
    "bottle": "bottle",
    "person": "person",
    "dining table": "table_surface",
}
PRODUCT_CLASSES = {"plate", "cup", "glass", "bottle", "tray"}

_GRACE_MS = 700   # geçiş sonrası titreme bastırma
_EDGE_MARGIN = 0.02  # normalize kenar payı — frame dışına çıkan track donar


@dataclass
class _TrackState:
    last_side: float = 0.0
    last_seen_ms: int = 0
    inside_zones: set[str] = field(default_factory=set)
    zone_enter_at: dict[str, int] = field(default_factory=dict)
    last_cross_ms: dict[str, int] = field(default_factory=dict)


class PassCounter:
    """Tek kamera için durumlu geçiş/sayım motoru."""

    def __init__(self, cam: CameraConfig, video_start_wall_ms: int, fps: float):
        self.cam = cam
        self.base_ms = video_start_wall_ms
        self.fps = fps
        self._tracks: dict[int, _TrackState] = {}

    def _ms(self, frame_idx: int) -> int:
        return self.base_ms + int(frame_idx / self.fps * 1000)

    def process(self, frame_idx: int, dets: list[dict]) -> list[VisionEvent]:
        """dets: [{track_id, object_class, bbox(x1,y1,x2,y2 px), confidence}]"""
        events: list[VisionEvent] = []
        now = self._ms(frame_idx)
        seen: set[int] = set()
        for d in dets:
            tid = d["track_id"]
            seen.add(tid)
            st = self._tracks.setdefault(tid, _TrackState())
            st.last_seen_ms = now
            c = bbox_center(d["bbox"], self.cam.resolution)
            if (c[0] < _EDGE_MARGIN or c[1] < _EDGE_MARGIN or
                    c[0] > 1 - _EDGE_MARGIN or c[1] > 1 - _EDGE_MARGIN):
                continue  # kenarda -> güvenilir değil
            # PASS çizgileri
            for line in self.cam.pass_lines:
                if not line.enabled:
                    continue
                side = side_of_line(line.a, line.b, c)
                if side == 0:
                    continue
                prev = st.last_side
                if prev != 0 and side != prev:
                    if now - st.last_cross_ms.get(line.zone_id, 0) > _GRACE_MS:
                        # Sözlesme: a USTTEN b ALTA cizilir -> +1 tarafi SOL
                        # = mutfak. Sol tarastan saga gecen "out" sayilir.
                        direction = "out" if prev > 0 else "in"
                        st.last_cross_ms[line.zone_id] = now
                        events.append(self._mk(
                            VisionEventType.OBJECT_CROSSED, d, tid, now,
                            frame_idx, line.zone_id, direction))
                st.last_side = side
            # Poligon zone'ları (giriş/çıkış)
            for z in self.cam.zones:
                if not z.enabled:
                    continue
                inside = point_in_polygon(c, z.polygon)
                was = z.zone_id in st.inside_zones
                if inside and not was:
                    st.zone_enter_at[z.zone_id] = now
                    st.inside_zones.add(z.zone_id)
                    events.append(self._mk(
                        VisionEventType.OBJECT_ENTERED, d, tid, now,
                        frame_idx, z.zone_id, None))
                elif not inside and was:
                    entered_at = st.zone_enter_at.get(z.zone_id, now)
                    if now - entered_at >= z.min_dwell_ms:
                        st.inside_zones.discard(z.zone_id)
                        events.append(self._mk(
                            VisionEventType.OBJECT_EXITED, d, tid, now,
                            frame_idx, z.zone_id, None))
        return events

    def _mk(self, etype, d, tid, now, frame_idx, zone_id, direction) -> VisionEvent:
        return VisionEvent(
            event_id=str(uuid.uuid4()), event_type=etype, occurred_at_ms=now,
            venue_id=self.cam.camera_id.replace("cam", "venue-"),  # yerinde config ile değişir
            camera_id=self.cam.camera_id, track_id=tid,
            object_class=d["object_class"], zone_id=zone_id,
            direction=direction, confidence=d["confidence"], frame_idx=frame_idx,
            bbox=tuple(d["bbox"]))
