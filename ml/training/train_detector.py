"""
Fine-tune YOLOv8-nano to detect dog noses, then export ONNX for FastAPI.

Usage (Python 3.11/3.12 recommended — not 3.14):
    python train_detector.py
    python train_detector.py --epochs 40 --batch 8 --imgsz 640
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_YAML = ML_ROOT / "data" / "detector" / "dog_nose_yolov8" / "data.yaml"
RUNS_DIR = ML_ROOT / "runs" / "detector"
BACKEND_MODELS = ML_ROOT.parent / "backend" / "models"


def _ensure_dataset(data_yaml: Path) -> None:
    if not data_yaml.exists():
        raise FileNotFoundError(
            f"Dataset yaml not found: {data_yaml}\n"
            "Put a YOLOv8 export under ml/data/detector/ or pass --data"
        )
    images = data_yaml.parent / "train" / "images"
    labels = data_yaml.parent / "train" / "labels"
    n_img = len(list(images.glob("*"))) if images.exists() else 0
    n_lab = len(list(labels.glob("*.txt"))) if labels.exists() else 0
    if n_img < 50 or n_lab < 50:
        raise RuntimeError(
            f"Dataset looks incomplete (images={n_img}, labels={n_lab}). "
            f"Check {data_yaml.parent}"
        )
    print(f"Dataset OK: {n_img} train images, {n_lab} labels @ {data_yaml}")


def train(args: argparse.Namespace) -> Path:
    from ultralytics import YOLO

    data_yaml = Path(args.data)
    _ensure_dataset(data_yaml)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    last_pt = RUNS_DIR / args.name / "weights" / "last.pt"

    if args.resume:
        if not last_pt.exists():
            raise FileNotFoundError(f"Cannot resume: {last_pt} not found")
        print(f"Resuming from {last_pt}")
        model = YOLO(str(last_pt))
        model.train(resume=True)
    else:
        model = YOLO(args.weights)
        model.train(
            data=str(data_yaml),
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            device=args.device,
            project=str(RUNS_DIR),
            name=args.name,
            exist_ok=True,
            patience=args.patience,
            workers=args.workers,
            pretrained=True,
            plots=False,
            verbose=False,
            cache="disk",
            save=True,
        )

    best = RUNS_DIR / args.name / "weights" / "best.pt"
    if not best.exists():
        raise FileNotFoundError(f"Training finished but {best} was not created")
    print(f"Best weights: {best}")
    return best


def export_onnx(weights: Path, output: Path, imgsz: int) -> Path:
    from ultralytics import YOLO

    output.parent.mkdir(parents=True, exist_ok=True)
    model = YOLO(str(weights))
    exported = model.export(
        format="onnx",
        imgsz=imgsz,
        opset=12,
        simplify=True,
        dynamic=False,
        nms=False,
    )
    exported_path = Path(exported)
    shutil.copy2(exported_path, output)
    print(f"Copied ONNX → {output}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Train YOLOv8-nano dog-nose detector")
    parser.add_argument("--weights", default="yolov8n.pt", help="Base checkpoint")
    parser.add_argument(
        "--data",
        default=str(DEFAULT_DATA_YAML),
        help="Path to data.yaml (default: dog_nose_yolov8)",
    )
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="0", help="'0' for first GPU, 'cpu' otherwise")
    parser.add_argument("--patience", type=int, default=15)
    parser.add_argument("--workers", type=int, default=0, help="0 is safest on Windows")
    parser.add_argument("--name", default="yolov8n-nose")
    parser.add_argument("--resume", action="store_true", help="Continue from last.pt")
    parser.add_argument("--skip-export", action="store_true")
    parser.add_argument(
        "--export-path",
        default=str(BACKEND_MODELS / "nose_detector.onnx"),
        help="Where to write the ONNX export",
    )
    args = parser.parse_args()

    print(f"Python {sys.version}")
    best = train(args)
    if args.skip_export:
        return
    export_onnx(best, Path(args.export_path), args.imgsz)


if __name__ == "__main__":
    main()
