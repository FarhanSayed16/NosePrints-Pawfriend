"""
Phase 1: build ml/data/detector/merged_v1 from existing Roboflow export +
synthetic hard-negative backgrounds + offline photometric/geometry copies.

No external API required. Does not touch identity data.
"""

from __future__ import annotations

import hashlib
import json
import random
import shutil
from pathlib import Path

import cv2
import numpy as np

ML_ROOT = Path(__file__).resolve().parents[1]
SRC = ML_ROOT / "data" / "detector" / "dog_nose_yolov8"
OUT = ML_ROOT / "data" / "detector" / "merged_v1"
NEG = ML_ROOT / "data" / "detector" / "negatives"
MANIFEST = OUT / "build_manifest.json"


def _copy_split(split_src: str, split_dst: str) -> dict:
    img_src = SRC / split_src / "images"
    lab_src = SRC / split_src / "labels"
    img_dst = OUT / split_dst / "images"
    lab_dst = OUT / split_dst / "labels"
    img_dst.mkdir(parents=True, exist_ok=True)
    lab_dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for img in sorted(img_src.glob("*")):
        if img.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
            continue
        stem = img.stem
        lab = lab_src / f"{stem}.txt"
        shutil.copy2(img, img_dst / img.name)
        if lab.exists():
            shutil.copy2(lab, lab_dst / f"{stem}.txt")
        else:
            (lab_dst / f"{stem}.txt").write_text("", encoding="utf-8")
        n += 1
    return {"copied": n}


def _make_keyboard(size: int = 640) -> np.ndarray:
    img = np.full((size, size, 3), 35, dtype=np.uint8)
    gap, key = 6, 36
    for y in range(12, size - key, key + gap):
        for x in range(12, size - key, key + gap):
            cv2.rectangle(img, (x, y), (x + key, y + key), (70, 72, 78), -1)
            cv2.rectangle(img, (x, y), (x + key, y + key), (140, 140, 145), 1)
    return img


def _make_fabric(size: int = 640) -> np.ndarray:
    img = np.full((size, size, 3), 210, dtype=np.uint8)
    colors = [(40, 90, 220), (40, 200, 220), (60, 40, 200), (180, 80, 40)]
    step = size // 8
    for yi, y in enumerate(range(0, size, step)):
        for xi, x in enumerate(range(0, size, step)):
            c = colors[(yi + xi) % len(colors)]
            pts = np.array([[x, y], [x + step, y], [x + step // 2, y + step]], np.int32)
            cv2.fillConvexPoly(img, pts, c)
    return img


def _make_blank(size: int = 640, shade: int = 180) -> np.ndarray:
    img = np.full((size, size, 3), shade, dtype=np.uint8)
    noise = np.random.default_rng(shade).integers(0, 8, img.shape, dtype=np.uint8)
    return cv2.add(img, noise)


def _make_ui(size: int = 640) -> np.ndarray:
    img = np.full((size, size, 3), 245, dtype=np.uint8)
    cv2.rectangle(img, (40, 40), (size - 40, 120), (30, 120, 220), -1)
    cv2.rectangle(img, (40, 160), (size - 40, size - 40), (230, 230, 230), -1)
    for i in range(6):
        y = 180 + i * 70
        cv2.rectangle(img, (60, y), (size - 60, y + 40), (200, 200, 205), -1)
        cv2.putText(img, "Button / Menu", (80, y + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 80, 80), 2)
    return img


def _make_fur(size: int = 640) -> np.ndarray:
    rng = np.random.default_rng(11)
    base = np.full((size, size, 3), (110, 120, 130), dtype=np.uint8)
    noise = rng.integers(0, 35, (size, size, 3), dtype=np.uint8)
    img = cv2.add(base, noise)
    for i in range(0, size, 4):
        shade = int(80 + (i % 50))
        cv2.line(img, (0, i), (size, i + 12), (shade, shade + 6, shade + 12), 1, cv2.LINE_AA)
    return img


def generate_negatives(n_each: int = 40) -> int:
    NEG.mkdir(parents=True, exist_ok=True)
    makers = {
        "keyboard": _make_keyboard,
        "fabric": _make_fabric,
        "blank": lambda: _make_blank(640, 175),
        "blank_dark": lambda: _make_blank(640, 40),
        "ui": _make_ui,
        "fur": _make_fur,
    }
    total = 0
    for name, fn in makers.items():
        for i in range(n_each):
            img = fn()
            # slight random brightness jitter
            alpha = 0.85 + 0.3 * (i / max(n_each - 1, 1))
            img = np.clip(img.astype(np.float32) * alpha, 0, 255).astype(np.uint8)
            path = NEG / f"{name}_{i:03d}.jpg"
            cv2.imwrite(str(path), img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            total += 1
    return total


def add_negatives_to_split(split: str, fraction_to_train: float = 0.85) -> int:
    imgs = sorted(NEG.glob("*.jpg"))
    rng = random.Random(42)
    rng.shuffle(imgs)
    cut = int(len(imgs) * fraction_to_train)
    mapping = {"train": imgs[:cut], "valid": imgs[cut:]}
    chosen = mapping.get(split, [])
    img_dst = OUT / split / "images"
    lab_dst = OUT / split / "labels"
    for p in chosen:
        shutil.copy2(p, img_dst / f"neg_{p.name}")
        (lab_dst / f"neg_{p.stem}.txt").write_text("", encoding="utf-8")
    return len(chosen)


def offline_augment_train(max_extra: int = 1200) -> int:
    """Photometric + light geometric copies of train images with remapped YOLO labels."""
    img_dir = OUT / "train" / "images"
    lab_dir = OUT / "train" / "labels"
    sources = [p for p in img_dir.glob("*") if not p.name.startswith("neg_")]
    rng = np.random.default_rng(7)
    made = 0
    for img_path in sources:
        if made >= max_extra:
            break
        lab_path = lab_dir / f"{img_path.stem}.txt"
        if not lab_path.exists():
            continue
        lines = [ln.strip() for ln in lab_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if not lines:
            continue
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        h, w = img.shape[:2]
        # brightness / contrast
        alpha = float(rng.uniform(0.75, 1.25))
        beta = float(rng.uniform(-25, 25))
        aug = np.clip(img.astype(np.float32) * alpha + beta, 0, 255).astype(np.uint8)
        # optional horizontal flip
        flip = bool(rng.integers(0, 2))
        new_lines = []
        if flip:
            aug = cv2.flip(aug, 1)
            for ln in lines:
                parts = ln.split()
                if len(parts) < 5:
                    continue
                cls, xc, yc, bw, bh = parts[0], float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                xc = 1.0 - xc
                new_lines.append(f"{cls} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")
        else:
            new_lines = lines
        # slight Gaussian blur sometimes
        if rng.random() < 0.35:
            aug = cv2.GaussianBlur(aug, (3, 3), 0)
        out_stem = f"aug_{img_path.stem}_{made:04d}"
        cv2.imwrite(str(img_dir / f"{out_stem}.jpg"), aug, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        (lab_dir / f"{out_stem}.txt").write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        made += 1
    return made


def write_data_yaml() -> None:
    yaml = f"""# merged_v1 — Roboflow Dog_nose + synthetic negatives + offline augs
path: {OUT.as_posix()}
train: train/images
val: valid/images
test: test/images

nc: 1
names: ['dog-nose']
"""
    (OUT / "data.yaml").write_text(yaml, encoding="utf-8")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    stats = {
        "train": _copy_split("train", "train"),
        "valid": _copy_split("valid", "valid"),
        "test": _copy_split("test", "test"),
    }
    n_neg_files = generate_negatives(40)
    n_neg_train = add_negatives_to_split("train")
    n_neg_val = add_negatives_to_split("valid")
    n_aug = offline_augment_train(1200)
    write_data_yaml()

    def count_split(split: str) -> int:
        return len(list((OUT / split / "images").glob("*")))

    summary = {
        "source": str(SRC),
        "output": str(OUT),
        "copied": stats,
        "synthetic_negatives_generated": n_neg_files,
        "negatives_in_train": n_neg_train,
        "negatives_in_valid": n_neg_val,
        "offline_augs_train": n_aug,
        "final_counts": {
            "train": count_split("train"),
            "valid": count_split("valid"),
            "test": count_split("test"),
            "total": count_split("train") + count_split("valid") + count_split("test"),
        },
    }
    MANIFEST.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
