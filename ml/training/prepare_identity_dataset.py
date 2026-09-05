"""
Rearrange CVPR 2022 Pet Biometric files into the folder layout ArcFace training expects:

    ml/data/identity/
        train/<dog_id>/*.jpg
        val/<dog_id>/*.jpg

The Kaggle dump is usually:

    pet_biometric_challenge_2022/train/images/*.jpg
    pet_biometric_challenge_2022/train/train_data.csv   (image name + dog id)

Usage:
    python prepare_identity_dataset.py --src ../data/identity/raw/pet_biometric_challenge_2022
"""

from __future__ import annotations

import argparse
import csv
import os
import random
import shutil
from collections import defaultdict
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ML_ROOT / "data" / "identity"


def _find_csv(train_dir: Path) -> Path | None:
    for name in ("train_data.csv", "train.csv", "label.csv", "labels.csv"):
        p = train_dir / name
        if p.exists():
            return p
    csvs = list(train_dir.glob("*.csv"))
    return csvs[0] if csvs else None


def _pick_columns(fieldnames: list[str]) -> tuple[str, str]:
    image_col = None
    id_col = None
    for name in fieldnames:
        key = name.lower().strip()
        if id_col is None and (
            key in {"dog id", "dog_id", "label", "identity", "class"}
            or ("dog" in key and "id" in key)
        ):
            id_col = name
            continue
        if image_col is None and (
            "image" in key or "file" in key or "print" in key or key in {"name", "img"}
        ):
            image_col = name
    if image_col is None or id_col is None:
        raise ValueError(f"Cannot detect image/id columns in {fieldnames}")
    return image_col, id_col


def _windows_safe_name(name: str) -> str:
    for ch in '*?:|"<>\\':
        name = name.replace(ch, "_")
    return name


def _collect_from_csv(src: Path) -> dict[str, list[Path]]:
    train_dir = src / "train"
    images_dir = train_dir / "images"
    if not images_dir.exists():
        images_dir = train_dir
    csv_path = _find_csv(train_dir)
    if csv_path is None:
        raise FileNotFoundError(
            f"No CSV labels under {train_dir}. Expected train_data.csv next to images/."
        )
    print(f"Indexing {images_dir} ...", flush=True)
    available = {p.name: p for p in images_dir.iterdir() if p.is_file()}
    print(f"Indexed {len(available)} files. Reading {csv_path.name} ...", flush=True)
    by_dog: dict[str, list[Path]] = defaultdict(list)
    missing = 0
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"{csv_path} has no header")
        image_col, id_col = _pick_columns(list(reader.fieldnames))
        print(f"Columns: image={image_col!r} id={id_col!r}", flush=True)
        for row in reader:
            name = Path(str(row[image_col]).strip()).name
            dog_id = str(row[id_col]).strip()
            if not name or not dog_id:
                continue
            path = available.get(name) or available.get(_windows_safe_name(name))
            if path is None:
                missing += 1
                continue
            by_dog[dog_id].append(path)
    if missing:
        print(f"CSV rows whose file was missing: {missing}", flush=True)
    return by_dog


def _collect_already_foldered(src: Path) -> dict[str, list[Path]]:
    by_dog: dict[str, list[Path]] = defaultdict(list)
    for dog_dir in sorted(p for p in src.iterdir() if p.is_dir()):
        imgs = [
            p
            for p in dog_dir.iterdir()
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        ]
        if imgs:
            by_dog[dog_dir.name].extend(imgs)
    return by_dog


def _place(src_img: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return
    try:
        os.link(src_img, dest)
    except OSError:
        shutil.copy2(src_img, dest)


def split_and_copy(
    by_dog: dict[str, list[Path]],
    out_dir: Path,
    min_images: int,
    val_ratio: float,
    seed: int,
) -> None:
    rng = random.Random(seed)
    train_root = out_dir / "train"
    val_root = out_dir / "val"
    for folder in (train_root, val_root):
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True, exist_ok=True)

    kept = 0
    skipped = 0
    for dog_id, paths in by_dog.items():
        paths = [p for p in paths if p.exists()]
        if len(paths) < min_images:
            skipped += 1
            continue
        rng.shuffle(paths)
        n_val = max(1, int(round(len(paths) * val_ratio))) if len(paths) >= 3 else 1
        n_val = min(n_val, len(paths) - 1)
        val_paths = paths[:n_val]
        train_paths = paths[n_val:]
        dest_train = train_root / dog_id
        dest_val = val_root / dog_id
        dest_train.mkdir(parents=True, exist_ok=True)
        dest_val.mkdir(parents=True, exist_ok=True)
        for src_img in train_paths:
            _place(src_img, dest_train / src_img.name)
        for src_img in val_paths:
            _place(src_img, dest_val / src_img.name)
        kept += 1
        if kept % 500 == 0:
            print(f"  ... {kept} dogs")

    print(
        f"Prepared {kept} dogs (>={min_images} images) -> {out_dir}\n"
        f"Skipped {skipped} dogs with too few photos"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare identity folders for ArcFace training")
    parser.add_argument(
        "--src",
        type=Path,
        required=True,
        help="Unzipped pet_biometric_challenge_2022 folder, or a folder of dog_id subdirs",
    )
    parser.add_argument("--out", type=Path, default=OUT_ROOT)
    parser.add_argument("--min-images", type=int, default=2)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    src = args.src.resolve()
    out_dir = args.out.resolve()
    if not src.exists():
        raise FileNotFoundError(src)
    print(f"Source: {src}", flush=True)
    print(f"Output: {out_dir}", flush=True)
    if src == out_dir or src.is_relative_to(out_dir / "train") or src.is_relative_to(out_dir / "val"):
        raise SystemExit("Source must not sit inside the train/val output folders")

    if (src / "train").exists():
        by_dog = _collect_from_csv(src)
    else:
        by_dog = _collect_already_foldered(src)

    if not by_dog:
        raise SystemExit(f"No labeled images found under {src}")

    print(f"Found {sum(len(v) for v in by_dog.values())} images across {len(by_dog)} dogs")
    split_and_copy(by_dog, out_dir, args.min_images, args.val_ratio, args.seed)


if __name__ == "__main__":
    main()
