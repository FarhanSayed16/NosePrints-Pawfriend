"""
Synthetic G1 fixtures — no copyrighted photos; generated with OpenCV/numpy.

Used to assert heuristic rejects (keyboard, blank) and likeness accepts (blob).
"""

from pathlib import Path

import cv2
import numpy as np

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def make_keyboard(path: Path | None = None, size: int = 320) -> bytes:
    """Grid of key-like rectangles — high edge density + grid regularity."""
    img = np.full((size, size, 3), 40, dtype=np.uint8)
    gap = 4
    key = 28
    for y in range(8, size - key, key + gap):
        for x in range(8, size - key, key + gap):
            cv2.rectangle(img, (x, y), (x + key, y + key), (70, 70, 75), -1)
            cv2.rectangle(img, (x, y), (x + key, y + key), (120, 120, 125), 1)
            cv2.putText(
                img,
                "A",
                (x + 8, y + 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (200, 200, 200),
                1,
                cv2.LINE_AA,
            )
    return _maybe_write(path, img)


def make_blank_wall(path: Path | None = None, size: int = 320) -> bytes:
    img = np.full((size, size, 3), 180, dtype=np.uint8)
    noise = np.random.default_rng(0).integers(0, 6, img.shape, dtype=np.uint8)
    img = cv2.add(img, noise)
    return _maybe_write(path, img)


def make_nose_like(path: Path | None = None, size: int = 256) -> bytes:
    """
    Dark elliptical center with lighter border + mild texture —
    enough for classical likeness, not a real biometric.
    """
    img = np.full((size, size, 3), 160, dtype=np.uint8)
    rng = np.random.default_rng(1)
    noise = rng.integers(0, 18, img.shape, dtype=np.uint8)
    img = cv2.subtract(img, noise // 2)
    center = (size // 2, size // 2)
    axes = (int(size * 0.32), int(size * 0.28))
    cv2.ellipse(img, center, axes, 0, 0, 360, (35, 32, 30), -1)
    cv2.ellipse(img, center, axes, 0, 0, 360, (55, 50, 48), 2)
    # Mild leather-ish texture inside
    y0, y1 = center[1] - axes[1], center[1] + axes[1]
    x0, x1 = center[0] - axes[0], center[0] + axes[0]
    roi = img[max(0, y0) : min(size, y1), max(0, x0) : min(size, x1)]
    tex = rng.integers(0, 25, roi.shape, dtype=np.uint8)
    roi[:] = cv2.add(roi, tex // 3)
    return _maybe_write(path, img)


def _maybe_write(path: Path | None, img: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    assert ok
    data = buf.tobytes()
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return data


def make_fabric_pattern(path: Path | None = None, size: int = 256) -> bytes:
    """Multi-colour triangle blanket — high colorfulness / hue spread."""
    img = np.full((size, size, 3), 220, dtype=np.uint8)
    colors = [
        (40, 90, 220),   # blue-ish
        (40, 200, 220),  # yellow
        (60, 40, 200),   # red
        (180, 80, 40),   # teal
    ]
    step = size // 4
    for yi, y in enumerate(range(0, size, step)):
        for xi, x in enumerate(range(0, size, step)):
            c = colors[(yi + xi) % len(colors)]
            pts = np.array(
                [[x, y], [x + step, y], [x + step // 2, y + step]],
                dtype=np.int32,
            )
            cv2.fillConvexPoly(img, pts, c)
            cv2.rectangle(img, (x, y), (x + step - 1, y + step - 1), (30, 30, 30), 1)
    return _maybe_write(path, img)


def make_fur_like(path: Path | None = None, size: int = 256) -> bytes:
    """Uniform mid-tone fur texture — no dark/pink leather center (body/back shot)."""
    rng = np.random.default_rng(7)
    base = np.full((size, size, 3), (118, 128, 138), dtype=np.uint8)
    noise = rng.integers(0, 28, (size, size, 3), dtype=np.uint8)
    img = cv2.add(base, noise)
    # Fine isotropic speckles (fur), not a dark ellipse
    for _ in range(400):
        x = int(rng.integers(0, size))
        y = int(rng.integers(0, size))
        shade = int(rng.integers(90, 150))
        cv2.circle(img, (x, y), 1, (shade, shade + 5, shade + 10), -1)
    return _maybe_write(path, img)


def ensure_fixtures() -> dict[str, Path]:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "keyboard": FIXTURE_DIR / "keyboard.jpg",
        "blank_wall": FIXTURE_DIR / "blank_wall.jpg",
        "nose_like": FIXTURE_DIR / "nose_like.jpg",
        "fabric": FIXTURE_DIR / "fabric.jpg",
        "fur_like": FIXTURE_DIR / "fur_like.jpg",
    }
    make_keyboard(paths["keyboard"])
    make_blank_wall(paths["blank_wall"])
    make_nose_like(paths["nose_like"])
    make_fabric_pattern(paths["fabric"])
    make_fur_like(paths["fur_like"])
    return paths


if __name__ == "__main__":
    ensure_fixtures()
    print(f"Wrote fixtures to {FIXTURE_DIR}")
