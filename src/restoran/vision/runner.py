"""Video dosyası üzerinde uçtan uca vision çalıştırıcısı.

Kullanım:
    python -m restoran.vision.runner data/test.mp4 \
        --scene config/scene.json --out data/vision_events.jsonl \
        [--emit-postgres]

YOLO antrenmanı yoktur; COCO önceden eğitilmiş ağırlıklar kullanılır.
Model ağırlığı ilk çalıştırmada otomatik indirilir (yolo11n.pt vb.).
"""
from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path

import cv2

from ..config.zones import SceneConfig
from .detector import DetectionRunner
from .pipeline import PassCounter


def run_video(video_path: Path, scene: SceneConfig, weights: str = "yolo11n.pt",
              conf: float = 0.35, on_event=None, max_frames: int | None = None,
              speed: float = 0.0, start_ms: int | None = None,
              force_class: str | None = None) -> list:
    """Videodan VisionEvent listesi üretir. on_event(event) opsiyonel canlı callback.

    start_ms verilirse event timestamp'leri o taban saat üzerine kare_ofset
    eklenerek hesaplanır (mock POS ile ayni zaman cizgisine oturtmak icin).
    """
    cam = scene.cameras[0]
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Video açılamadı: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or cam.fps
    start_wall = start_ms if start_ms is not None else int(time.time() * 1000)
    counter = PassCounter(cam, video_start_wall_ms=start_wall, fps=fps)
    runner = DetectionRunner(weights, cam.resolution, conf)
    _fc = force_class

    events = []
    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        dets = runner.track(frame, force_class=_fc)
        for ev in counter.process(frame_idx, dets):
            ev.venue_id = scene.venue_id
            ev.video_path = str(video_path)
            events.append(ev)
            if on_event:
                on_event(ev)
        if speed > 0:
            time.sleep(1.0 / fps / max(speed, 0.1))
        frame_idx += 1
        if max_frames and frame_idx >= max_frames:
            break
    cap.release()
    return events


def main() -> None:
    ap = argparse.ArgumentParser(description="Videodan VisionEvent üret")
    ap.add_argument("video", type=Path)
    ap.add_argument("--scene", type=Path, required=True, help="SceneConfig JSON")
    ap.add_argument("--out", type=Path, default=Path("vision_events.jsonl"))
    ap.add_argument("--weights", default="yolo11n.pt")
    ap.add_argument("--conf", type=float, default=0.35)
    ap.add_argument("--max-frames", type=int, default=None)
    ap.add_argument("--start-ms", type=int, default=None,
                    help="event zaman tabani (mock POS ile esitlemek icin)")
    ap.add_argument("--http", default=None,
                    help="event'leri JSONL yerine POST bu URL'ye gonder (ornegin "
                         "http://localhost:8100/ingest/vision); --stream ile Canli)")
    ap.add_argument("--force-class", default=None,
                    help="demo harness: algilanan sinifi zorla buna esle (plate vb.)")
    ap.add_argument("--stream", action="store_true",
                    help="--http ile birlikte: kare kare ilerleyerek gonder (panelde canli akis)")
    ap.add_argument("--speed", type=float, default=1.0,
                    help="--stream gercek zaman hiz carpani (4 = 4x hizli)")
    args = ap.parse_args()

    scene = SceneConfig.model_validate(json.loads(args.scene.read_text()))
    t0 = time.time()

    sender = None
    if args.http:
        import httpx
        client = httpx.Client(timeout=10)

        def sender(ev, _c=client, _url=args.http):
            _c.post(_url, json=[ev.model_dump(mode="json")])

    events = run_video(args.video, scene, weights=args.weights, conf=args.conf,
                       max_frames=args.max_frames, start_ms=args.start_ms,
                       on_event=sender if args.stream else None,
                       speed=args.speed if args.stream else 0.0,
                       force_class=args.force_class)
    if args.http and not args.stream and sender:
        for ev in events:
            sender(ev)
    with args.out.open("w") as f:
        for ev in events:
            f.write(ev.model_dump_json() + "\n")
    crossed = sum(1 for e in events if e.event_type == "OBJECT_CROSSED")
    print(f"{len(events)} event ({crossed} PASS geçişi) -> {args.out} "
          f"[{time.time() - t0:.1f}s]")


if __name__ == "__main__":
    main()
