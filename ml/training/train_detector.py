"""
Fine-tune YOLOv8-nano to detect dog noses, then export ONNX for FastAPI.

Phone Stage-2 recipe (RTX 4050 6GB), after phone_v1 labels exist:

    python train_detector.py ^
      --weights ..\\runs\\detector\\yolov8n-nose-merged-v1\\weights\\best.pt ^
      --data ..\\data\\detector\\phone_v1\\data.yaml ^
      --epochs 50 --batch 16 --imgsz 640 --patience 15 ^
      --scale 0.55 --mosaic 1.0 --hsv-s 0.5 --hsv-v 0.4 ^
      --name yolov8n-nose-phone-v1 ^
      --export-path ..\\..\\backend\\models\\nose_detector.candidate.onnx

Promote candidate only via scripts/promote_nose_onnx.py after phone_eval improves.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_YAML = ML_ROOT / "data" / "detector" / "dog_nose_yolov8" / "data.yaml"
DEFAULT_MERGED_WEIGHTS = (
    ML_ROOT / "runs" / "detector" / "yolov8n-nose-merged-v1" / "weights" / "best.pt"
)
RUNS_DIR = ML_ROOT / "runs" / "detector"
BACKEND_MODELS = ML_ROOT.parent / "backend" / "models"


def _ensure_dataset(data_yaml: Path, min_images: int) -> None:
    if not data_yaml.exists():
        raise FileNotFoundError(
            f"Dataset yaml not found: {data_yaml}\n"
            "Put a YOLOv8 export under ml/data/detector/ or pass --data"
        )
    images = data_yaml.parent / "train" / "images"
    labels = data_yaml.parent / "train" / "labels"
    n_img = len(list(images.glob("*"))) if images.exists() else 0
    n_lab = len(list(labels.glob("*.txt"))) if labels.exists() else 0
    if n_img < min_images or n_lab < min_images:
        raise RuntimeError(
            f"Dataset looks incomplete (images={n_img}, labels={n_lab}, "
            f"need >= {min_images}). Check {data_yaml.parent}"
        )
    print(f"Dataset OK: {n_img} train images, {n_lab} labels @ {data_yaml}")


def train(args: argparse.Namespace) -> Path:
    from ultralytics import YOLO

    data_yaml = Path(args.data)
    _ensure_dataset(data_yaml, min_images=args.min_images)
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
            # Phone domain gap: zoom-out + mosaic + mild HSV for wet/pink leather
            scale=args.scale,
            mosaic=args.mosaic,
            mixup=args.mixup,
            hsv_s=args.hsv_s,
            hsv_v=args.hsv_v,
            hsv_h=args.hsv_h,
            blur=args.blur,
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
    default_weights = (
        str(DEFAULT_MERGED_WEIGHTS) if DEFAULT_MERGED_WEIGHTS.exists() else "yolov8n.pt"
    )
    parser.add_argument(
        "--weights",
        default=default_weights,
        help="Base checkpoint (default: merged_v1 best.pt if present)",
    )
    parser.add_argument(
        "--data",
        default=str(DEFAULT_DATA_YAML),
        help="Path to data.yaml (default: dog_nose_yolov8)",
    )
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="0", help="'0' for first GPU, 'cpu' otherwise")
    parser.add_argument("--patience", type=int, default=15)
    parser.add_argument("--workers", type=int, default=0, help="0 is safest on Windows")
    parser.add_argument("--name", default="yolov8n-nose-phone-v1")
    parser.add_argument("--resume", action="store_true", help="Continue from last.pt")
    parser.add_argument("--skip-export", action="store_true")
    parser.add_argument(
        "--export-path",
        default=str(BACKEND_MODELS / "nose_detector.candidate.onnx"),
        help="Where to write the ONNX export (candidate by default — do not overwrite live)",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=0.45,
        help="Ultralytics scale aug (lower = more zoom-out / tiny-nose simulation)",
    )
    parser.add_argument("--mosaic", type=float, default=1.0)
    parser.add_argument("--mixup", type=float, default=0.1, help="MixUp probability")
    parser.add_argument("--hsv-s", type=float, default=0.5, dest="hsv_s")
    parser.add_argument("--hsv-v", type=float, default=0.4, dest="hsv_v")
    parser.add_argument("--hsv-h", type=float, default=0.015, dest="hsv_h")
    parser.add_argument("--blur", type=float, default=0.05, help="Blur augmentation probability")
    parser.add_argument(
        "--min-images",
        type=int,
        default=30,
        help="Minimum train images/labels before allowing train (phone_v1 gate)",
    )
    args = parser.parse_args()

    print(f"Python {sys.version}")
    print(
        f"weights={args.weights} data={args.data} epochs={args.epochs} "
        f"batch={args.batch} scale={args.scale} mosaic={args.mosaic}"
    )
    best = train(args)
    if args.skip_export:
        return
    export_onnx(best, Path(args.export_path), args.imgsz)


if __name__ == "__main__":
    main()
