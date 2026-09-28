"""Test videosu üreteci — gercek foto crop'lari PASS cizgisini keser.

YOLO'nun gercek dokuyla tespit edebilmesi icin bus.jpg'den kisi crop'lari alinir,
düz zemin üzerinde soldan sağa hareket ettirilir. Böylece:
  - tespit + takip (COCO person) gercek piksel dokusuyla calisir
  - PASS gecisi deterministik: kac gecis olacagi bilinen senaryo

Kullanim:
  .venv/bin/python tools/make_test_video.py            # data/pass_people.mp4 uretir
Cizim sozlesmesi: a->b vektorunun +1 tarafi mutfak. Dikey cizide a=alt, b=ust
secilirse sol taraf +1 olur -> sol->sag gecisi "out" (mutfaktan salon).
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / ".venv/lib/python3.12/site-packages/ultralytics/assets/bus.jpg"
OUT_VIDEO = ROOT / "data/pass_people.mp4"
OUT_SCENE = ROOT / "config/scene.passpeople.json"

W, H, FPS = 1280, 720, 25
PASS_X = 0.62


def person_crops() -> list[np.ndarray]:
    model = YOLO("yolo11n.pt")
    res = model.predict(str(SRC), conf=0.4, verbose=False)[0]
    img = res.orig_img
    crops = []
    for b in res.boxes:
        x1, y1, x2, y2 = (int(v) for v in b.xyxy[0])
        crop = img[y1:y2, x1:x2]
        if crop.size and (x2 - x1) > 60:
            crops.append(crop)
    return crops


def main() -> None:
    crops = person_crops()
    if not crops:
        raise SystemExit("crop alinamadi")
    # 3 yolcu, farkli hiz/ gecikme; her biri soldan saga PASS'i keser
    lanes = []
    for i, crop in enumerate(crops[:3]):
        ch, cw = crop.shape[:2]
        scale = min(1.0, 260.0 / ch)
        crop_r = cv2.resize(crop, (int(cw * scale), int(ch * scale)))
        lanes.append({"img": crop_r, "y": 300 + i * 60,
                      "speed": 4.0 + i * 1.2, "delay": i * 45})

    frames_dir = ROOT / "data/_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    total = 320
    for f in range(total):
        canvas = np.full((H, W, 3), (34, 38, 46), np.uint8)
        cv2.rectangle(canvas, (0, 560), (W, H), (52, 56, 66), -1)  # zemin bandi
        for ln in lanes:
            if f < ln["delay"]:
                continue
            x = int(-ln["img"].shape[1] + (f - ln["delay"]) * ln["speed"] * 6)
            if x > W:
                continue
            y = ln["y"] - ln["img"].shape[1] // 2
            paste_region(canvas, ln["img"], max(x, -ln["img"].shape[1] + 1), y)
        px = int(PASS_X * W)
        cv2.line(canvas, (px, 0), (px, H), (200, 200, 200), 2)
        cv2.imwrite(str(frames_dir / f"f{f:04d}.png"), canvas)

    import subprocess
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
         "-i", str(frames_dir / "f%04d.png"), "-c:v", "libx264",
         "-pix_fmt", "yuv420p", str(OUT_VIDEO)], check=True)
    for p in frames_dir.glob("*.png"):
        p.unlink()
    frames_dir.rmdir()

    scene = {
        "venue_id": "demo",
        "cameras": [{
            "camera_id": "cam0", "label": "PASS kisi senaryosu",
            "resolution": [W, H], "fps": float(FPS), "zones": [],
            "pass_lines": [{
                "zone_id": "pass-out", "kind": "pass_out", "label": "Mutfak cikisi",
                # a UST, b ALT -> +1 tarafi SOL = mutfak; sol->sag gecisi "out"
                "a": {"x": PASS_X, "y": 0.0}, "b": {"x": PASS_X, "y": 1.0}}]}],
    }
    OUT_SCENE.write_text(json.dumps(scene, indent=2))
    print(f"OK -> {OUT_VIDEO.name} ({total} kare), scene -> {OUT_SCENE.name}, "
          f"kisi sayisi: {len(lanes)}")


def paste_region(canvas: np.ndarray, img: np.ndarray, x: int, y: int) -> None:
    ih, iw = img.shape[:2]
    ch, cw = canvas.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + iw, cw), min(y + ih, ch)
    if x1 <= x0 or y1 <= y0:
        return
    sx0, sy0 = x0 - x, y0 - y
    canvas[y0:y1, x0:x1] = img[sy0:sy0 + (y1 - y0), sx0:sx0 + (x1 - x0)]


if __name__ == "__main__":
    main()
