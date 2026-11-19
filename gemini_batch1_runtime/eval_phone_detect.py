"""
Offline eval: two-stage dog→nose detect + look-gate on ml/data/phone_eval/*.

Usage (from repo, with backend PYTHONPATH):
  set PYTHONPATH=D:\\NosePrints-Pawfriend\\backend
  backend\\venv\\Scripts\\python.exe scripts\\eval_phone_detect.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.dog_detector import dog_detector
from app.services.look_gate import assess_look_photo
from app.services.nose_detector import nose_detector
from app.services.nose_heuristics import suggest_nose_bbox_norm


def main() -> int:
    folder = ROOT / "ml" / "data" / "phone_eval"
    folder.mkdir(parents=True, exist_ok=True)
    images = sorted(
        p
        for p in folder.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )
    if not images:
        print(f"No images in {folder}")
        print("Add failed phone JPEGs there, then re-run.")
        return 1

    nose_detector.load()
    dog_detector.load()
    print(f"nose_loaded={nose_detector.is_loaded} dog_loaded={dog_detector.is_loaded}")
    print(f"Evaluating {len(images)} images\n")

    for path in images:
        data = path.read_bytes()
        det = nose_detector.detect(data)
        hint = suggest_nose_bbox_norm(det.original, dog_bbox=det.dog_bbox)
        look = assess_look_photo(data)
        print(
            f"{path.name}: nose_conf={det.confidence:.3f} nose_box={det.bbox} "
            f"dog_conf={det.dog_confidence:.3f} dog_box={det.dog_bbox} "
            f"hint={hint is not None} look_soft={look.soft_warn} "
            f"look_issues={look.issues[:1]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
