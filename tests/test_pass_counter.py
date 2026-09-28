"""PassCounter birim testi — YOLO/camera gerektirmez, sahte detection listesi beslenir.

Geçiş mantığı, histeresis ve grace süresi doğrulanır.
Calıştırma: .venv/bin/python tests/test_pass_counter.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, "src")

from restoran.config.zones import CameraConfig, PassLine, Point, Zone
from restoran.vision.pipeline import PassCounter

CAM = CameraConfig(
    camera_id="cam0", resolution=(1000, 1000), fps=25.0,
    pass_lines=[PassLine(zone_id="pass-out", a=Point(x=0.5, y=0.0),
                         b=Point(x=0.5, y=1.0))],
    zones=[Zone(zone_id="t1", kind="table", polygon=[
        Point(x=0.0, y=0.0), Point(x=0.2, y=0.0),
        Point(x=0.2, y=0.2), Point(x=0.0, y=0.2)])])


def det(tid, cx, cy, cls="plate"):
    return {"track_id": tid, "object_class": cls,
            "bbox": (cx * 1000 - 20, cy * 1000 - 20, cx * 1000 + 20, cy * 1000 + 20),
            "confidence": 0.9}


def main() -> None:
    pc = PassCounter(CAM, video_start_wall_ms=1_000_000_000_000, fps=25.0)
    events = []

    # frame 0-2: mutfak tarafı (x=0.3)
    for f in range(3):
        events += pc.process(f, [det(1, 0.3, 0.5)])
    # frame 3: çizgiye yapışık (x=0.5 -> side 0) - geçiş sayılmamalı
    events += pc.process(3, [det(1, 0.5, 0.5)])
    # frame 4: x=0.7 tarafı; mutfak +1 tarafı (cross=0.5-px > 0 ⇔ px<0.5),
    # yani 0.3 mutfak, 0.7 salon -> "out" geçişi
    events += pc.process(4, [det(1, 0.7, 0.5)])
    # frame 5: geri sıçrama (titreme) -> grace içinde, sayılmamalı
    events += pc.process(5, [det(1, 0.3, 0.5)])
    crossed = [e for e in events if e.event_type.value == "OBJECT_CROSSED"]
    assert len(crossed) == 1, f"tek geçiş beklenirdi, {len(crossed)} çıktı"
    assert crossed[0].direction == "out", "mutfaktan salona geçiş 'out' olmalı"

    # frame 100'de (2.4s sonra) tekrar salona geçiş -> sayılmalı (grace aşıldı)
    for f in range(100, 103):
        events += pc.process(f, [det(1, 0.7, 0.5)])
    crossed = [e for e in events if e.event_type.value == "OBJECT_CROSSED"]
    assert len(crossed) == 2, "grace sonrası ikinci geçiş sayılmalı"

    # masa zone girişi: tabak t1 poligonuna girerse OBJECT_ENTERED
    evs = pc.process(200, [det(2, 0.1, 0.1)])
    assert any(e.event_type.value == "OBJECT_ENTERED" and e.zone_id == "t1" for e in evs)

    # kenarındaki track (x=0.99) güvenilir değil -> hiçbir event üretmemeli
    n_before = len(events)
    edge = pc.process(201, [det(3, 0.995, 0.5)])
    assert edge == [], "kenar track filtrelenmeli"

    print("PASS COUNTER OK — geçiş/histeresis/grace/zone/kenar filtresi doğru")


if __name__ == "__main__":
    main()
