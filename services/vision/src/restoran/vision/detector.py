"""Ultralytics YOLO + ByteTrack/BoT-SORT ince sarmalayıcı.

Her kare için model.track(persist=True) çağrılır; COCO sınıf isimleri
kanonik nesne adlarına eşlenir (COCO_TO_OBJECT). Sadece işimize yarayan
sınıflar döner.
"""
from __future__ import annotations

from ultralytics import YOLO

from .pipeline import COCO_TO_OBJECT

# Takip edeceğimiz COCO sınıf id'leri (person dahil — kişi durum makineleri için)
_INTEREST = {"person", "bowl", "cup", "wine glass", "bottle", "dining table"}


class DetectionRunner:
    def __init__(self, weights: str, resolution: tuple[int, int], conf: float = 0.35,
                 tracker: str = "bytetrack.yaml"):
        self.model = YOLO(weights)
        self.conf = conf
        self.resolution = resolution
        self.tracker_cfg = tracker
        self.names = self.model.names  # id -> coco adı

    def track(self, frame_bgr, force_class: str | None = None) -> list[dict]:
        """Frame -> [{track_id, object_class, bbox px, confidence}] (filtreli).

        force_class: demo harness'i — algilanan sinifi zorla bu sinifa
        esler (orn. 'person' crop'lariyla 'plate' gecisi simule edilir).
        """
        res = self.model.track(
            frame_bgr, persist=True, conf=self.conf, verbose=False,
            tracker=self.tracker_cfg)
        boxes = res[0].boxes
        out: list[dict] = []
        if boxes is None or boxes.id is None:
            # idsiz tespitleri de sınıf bazında sayıya katarız (v0 toleransı)
            if boxes is not None:
                for b in boxes:
                    cname = self.names.get(int(b.cls), "")
                    obj = COCO_TO_OBJECT.get(cname)
                    if obj:
                        if force_class:
                            obj = force_class
                        x1, y1, x2, y2 = (float(v) for v in b.xyxy[0])
                        out.append({"track_id": -1, "object_class": obj,
                                    "bbox": (x1, y1, x2, y2),
                                    "confidence": float(b.conf)})
            return out
        for b in boxes:
            cid = int(b.cls)
            cname = self.names.get(cid, "")
            obj = COCO_TO_OBJECT.get(cname)
            if not obj:
                continue
            if force_class:
                obj = force_class
            x1, y1, x2, y2 = (float(v) for v in b.xyxy[0])
            out.append({"track_id": int(b.id), "object_class": obj,
                        "bbox": (x1, y1, x2, y2), "confidence": float(b.conf)})
        return out
