"""Geometri yardımcıları — normalized koordinat uzayında çalışır.

PASS çizgisi geçişi: centroid'ın çizginin hangi tarafında olduğunun işareti
değiştiğinde geçiş doğar. Yanlış alarmı kesmek için histeresis + grace period.
"""
from __future__ import annotations

import math

from .zones import PassLine, Point, Zone


def side_of_line(a: Point, b: Point, p: tuple[float, float]) -> float:
    """p noktası ab doğrusunun hangi tarafında: +1 / -1 (0 = üstünde).

    a USTTEN b ALTA dikey cizim: cross>0 <=> p cizginin SOLUNDE."""
    cross = (b.x - a.x) * (p[1] - a.y) - (b.y - a.y) * (p[0] - a.x)
    if abs(cross) < 1e-9:
        return 0.0
    return 1.0 if cross > 0 else -1.0


def point_in_polygon(p: tuple[float, float], polygon: list[Point]) -> bool:
    """Ray casting; kenar üstü içerde sayılır."""
    inside = False
    n = len(polygon)
    j = n - 1
    px, py = p
    for i in range(n):
        xi, yi = polygon[i].x, polygon[i].y
        xj, yj = polygon[j].x, polygon[j].y
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def polygon_centroid(polygon: list[Point]) -> tuple[float, float]:
    xs = [pt.x for pt in polygon]
    ys = [pt.y for pt in polygon]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def bbox_center(bbox: tuple[float, float, float, float],
                resolution: tuple[int, int]) -> tuple[float, float]:
    """Piksel bbox -> normalized centroid."""
    x1, y1, x2, y2 = bbox
    w, h = resolution
    return ((x1 + x2) / 2 / w, (y1 + y2) / 2 / h)


def line_distance(a: PassLine, p: tuple[float, float]) -> float:
    """Noktanın çizgiye uzaklığı (normalized birim) — grace filtresi için."""
    ax, ay, bx, by = a.a.x, a.a.y, a.b.x, a.b.y
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(p[0] - ax, p[1] - ay)
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    projx, projy = ax + t * dx, ay + t * dy
    return math.hypot(p[0] - projx, p[1] - projy)
