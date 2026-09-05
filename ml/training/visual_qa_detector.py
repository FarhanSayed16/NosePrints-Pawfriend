"""
Run the trained nose detector on held-out val images and save crops.
Used for visual QA (Phase 1 Definition of Done).

Usage:
    python visual_qa_detector.py
    python visual_qa_detector.py --weights ../runs/detector/yolov8n-nose/weights/best.pt
    python visual_qa_detector.py --onnx ../../backend/models/nose_detector.onnx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

ML_ROOT = Path(__file__).resolve().parents[1]
VAL_IMAGES = ML_ROOT / "data" / "detector" / "dog_nose_yolov8" / "valid" / "images"
VAL_LABELS = ML_ROOT / "data" / "detector" / "dog_nose_yolov8" / "valid" / "labels"
OUT_DIR = ML_ROOT / "eval_results" / "detector_qa"
BACKEND_ONNX = ML_ROOT.parent / "backend" / "models" / "nose_detector.onnx"


def _labeled_images(limit: int) -> list[Path]:
    """Prefer val images that actually have a nose box (dataset is ~60% background)."""
    labeled: list[Path] = []
    background: list[Path] = []
    for path in sorted(VAL_IMAGES.glob("*")):
        lab = VAL_LABELS / f"{path.stem}.txt"
        if lab.exists() and lab.stat().st_size > 0:
            labeled.append(path)
        else:
            background.append(path)
    chosen = labeled[:limit]
    if len(chosen) < limit:
        chosen.extend(background[: limit - len(chosen)])
    return chosen


def qa_ultralytics(weights: Path, limit: int) -> None:
    from ultralytics import YOLO

    model = YOLO(str(weights))
    images = _labeled_images(limit)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    hits = 0
    for i, path in enumerate(images):
        results = model.predict(str(path), conf=0.35, verbose=False)
        img = cv2.imread(str(path))
        if img is None:
            continue
        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            cv2.imwrite(str(OUT_DIR / f"{i:02d}_MISS_{path.stem[:40]}.jpg"), img)
            continue
        hits += 1
        xyxy = boxes.xyxy[0].cpu().numpy().astype(int)
        x1, y1, x2, y2 = xyxy.tolist()
        crop = img[max(0, y1) : max(0, y2), max(0, x1) : max(0, x2)]
        vis = img.copy()
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.imwrite(str(OUT_DIR / f"{i:02d}_box_{path.stem[:40]}.jpg"), vis)
        if crop.size:
            cv2.imwrite(str(OUT_DIR / f"{i:02d}_crop_{path.stem[:40]}.jpg"), crop)
    print(f"Ultralytics QA: {hits}/{len(images)} detections → {OUT_DIR}")


def qa_onnx(onnx_path: Path, limit: int) -> None:
    import importlib.util
    import types

    import onnxruntime as ort

    # Load NoseDetector without importing backend app.services.__init__ (heavy deps).
    config_mod = types.ModuleType("app.config")

    class _Settings:
        NOSE_DETECTOR_MODEL_PATH = str(onnx_path)
        DETECTOR_CONF_THRESHOLD = 0.35
        DETECTOR_RETRY_CONF_THRESHOLD = 0.20
        DETECTOR_CLOSEUP_PAD = 0.30

    config_mod.settings = _Settings()
    sys.modules.setdefault("app", types.ModuleType("app"))
    sys.modules["app.config"] = config_mod

    spec = importlib.util.spec_from_file_location(
        "nose_detector_standalone",
        ML_ROOT.parent / "backend" / "app" / "services" / "nose_detector.py",
    )
    if spec is None or spec.loader is None:
        raise ImportError("Could not load nose_detector.py")
    nd = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = nd
    spec.loader.exec_module(nd)

    detector = nd.NoseDetector()
    detector.session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    detector.input_name = detector.session.get_inputs()[0].name
    detector.input_shape = detector.session.get_inputs()[0].shape
    detector._loaded = True

    images = _labeled_images(limit)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    hits = 0
    for i, path in enumerate(images):
        data = path.read_bytes()
        result = detector.detect(data)
        if result.bbox is None:
            continue
        hits += 1
        if result.crop is not None:
            cv2.imwrite(str(OUT_DIR / f"onnx_{i:02d}_crop.jpg"), result.crop)
    print(f"ONNX QA: {hits}/{len(images)} detections → {OUT_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=Path, default=None)
    parser.add_argument("--onnx", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    if not VAL_IMAGES.exists():
        raise FileNotFoundError(VAL_IMAGES)

    default_pt = ML_ROOT / "runs" / "detector" / "yolov8n-nose" / "weights" / "best.pt"
    weights = args.weights or (default_pt if default_pt.exists() else None)
    onnx = args.onnx or (BACKEND_ONNX if BACKEND_ONNX.exists() else None)

    if weights and weights.exists():
        qa_ultralytics(weights, args.limit)
    if onnx and onnx.exists():
        qa_onnx(onnx, args.limit)
    if not weights and not onnx:
        raise SystemExit("No weights or ONNX found. Train first: python train_detector.py")


if __name__ == "__main__":
    main()
