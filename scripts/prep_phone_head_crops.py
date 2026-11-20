"""
Crop Stage-1 dog heads from field photos for fast Stage-2 labeling.

Puts head JPEGs in ml/data/detector/phone_v1/heads_to_label/ so the nose
fills most of the frame — label leather only, then move into train/images.

Usage (from backend/):
  set PYTHONPATH=D:\\NosePrints-Pawfriend\\backend
  venv\\Scripts\\python.exe ..\\scripts\\prep_phone_head_crops.py
  venv\\Scripts\\python.exe ..\\scripts\\prep_phone_head_crops.py --src ..\\ml\\data\\phone_eval
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.dog_detector import dog_detector
from app.services.image_io import decode_bgr


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--src",
        default=str(ROOT / "ml" / "data" / "phone_eval"),
        help="Folder of full phone JPEGs",
    )
    parser.add_argument(
        "--out",
        default=str(ROOT / "ml" / "data" / "detector" / "phone_v1" / "heads_to_label"),
        help="Where to write head crops",
    )
    args = parser.parse_args()

    src = Path(args.src)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    images = sorted(
        p for p in src.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )
    if not images:
        print(f"No images in {src}")
        return 1

    dog_detector.load()
    if not dog_detector.is_loaded:
        print("Dog detector failed to load — check backend/models/dog_detector_coco.onnx")
        return 1

    ok = 0
    miss = 0
    for path in images:
        if path.name.lower().startswith("junk_"):
            continue
        img = decode_bgr(path.read_bytes())
        hit = dog_detector.detect(img)
        if hit is None:
            print(f"MISS dog: {path.name}")
            miss += 1
            continue
        h, w = img.shape[:2]
        x1, y1, x2, y2 = dog_detector.head_roi(hit, h, w)
        crop = img[y1:y2, x1:x2]
        if crop.size == 0 or min(crop.shape[:2]) < 32:
            print(f"BAD crop: {path.name}")
            miss += 1
            continue
        dest = out / f"{path.stem}_head.jpg"
        cv2.imwrite(str(dest), crop, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        print(f"OK {path.name} → {dest.name} dog_conf={hit.confidence:.3f}")
        ok += 1

    print(f"\nWrote {ok} head crops to {out} (miss={miss})")
    print("Label tight nose leather on these, then copy into phone_v1/train/images + labels.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
