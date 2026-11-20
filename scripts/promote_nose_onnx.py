"""
Promote nose_detector.candidate.onnx → nose_detector.onnx only if phone_eval improves.

Compares mean Stage-2 nose_conf on ml/data/phone_eval dog-like images
(excluding junk_* names) between live and candidate ONNX.

Usage (from backend/):
  set PYTHONPATH=D:\\NosePrints-Pawfriend\\backend
  venv\\Scripts\\python.exe ..\\scripts\\promote_nose_onnx.py
  venv\\Scripts\\python.exe ..\\scripts\\promote_nose_onnx.py --force   # emergency only
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
MODELS = BACKEND / "models"
sys.path.insert(0, str(BACKEND))


def _eval_mean_nose_conf(onnx_path: Path, images: list[Path]) -> float:
    from app.config import settings
    from app.services.nose_detector import NoseDetector

    # Temporarily point settings path used by a fresh detector instance
    settings.NOSE_DETECTOR_MODEL_PATH = str(onnx_path)
    det = NoseDetector()
    det.load()
    if not det.is_loaded:
        raise RuntimeError(f"Could not load {onnx_path}")
    scores = []
    for path in images:
        result = det.detect(path.read_bytes())
        scores.append(float(result.confidence or 0.0))
    return sum(scores) / max(len(scores), 1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--candidate",
        default=str(MODELS / "nose_detector.candidate.onnx"),
    )
    parser.add_argument(
        "--live",
        default=str(MODELS / "nose_detector.onnx"),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip phone_eval gate (not recommended)",
    )
    args = parser.parse_args()

    candidate = Path(args.candidate)
    live = Path(args.live)
    if not candidate.exists():
        print(f"Candidate missing: {candidate}")
        print("Train with train_detector.py --export-path ...candidate.onnx first.")
        return 1
    if not live.exists():
        print(f"Live model missing: {live}")
        return 1

    folder = ROOT / "ml" / "data" / "phone_eval"
    images = sorted(
        p
        for p in folder.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        and not p.name.lower().startswith("junk_")
    )
    if len(images) < 1:
        print(f"No non-junk images in {folder}")
        return 1

    if not args.force:
        print(f"Evaluating live vs candidate on {len(images)} non-junk phone_eval images…")
        live_mean = _eval_mean_nose_conf(live, images)
        cand_mean = _eval_mean_nose_conf(candidate, images)
        print(f"live_mean_nose_conf={live_mean:.4f}")
        print(f"candidate_mean_nose_conf={cand_mean:.4f}")
        if cand_mean <= live_mean + 0.01:
            print("REFUSE promote: candidate did not improve phone_eval nose_conf.")
            print("Keep labeling / retrain. Use --force only in emergency.")
            return 2
    else:
        print("WARNING: --force set; skipping phone_eval gate.")

    backup = MODELS / "backups" / "nose_detector.before_promote.onnx"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(live, backup)
    shutil.copy2(candidate, live)
    print(f"Promoted {candidate.name} → {live.name}")
    print(f"Previous live backed up to {backup}")
    print("Restart the API process to reload the detector.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
