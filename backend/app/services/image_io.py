"""
Image decode helpers — apply EXIF orientation so phone photos are upright
before YOLO / heuristics (OpenCV imdecode alone ignores EXIF).
"""

from __future__ import annotations

import io

import cv2
import numpy as np
from PIL import Image, ImageOps


def decode_bgr(image_bytes: bytes) -> np.ndarray:
    """
    Decode JPEG/PNG bytes to BGR uint8 with EXIF orientation applied.
    Raises ValueError if the bytes are not a readable image.
    """
    if not image_bytes:
        raise ValueError("Could not decode image")

    # Prefer Pillow so EXIF Orientation is honored (phone gallery / camera).
    try:
        pil = Image.open(io.BytesIO(image_bytes))
        pil = ImageOps.exif_transpose(pil)
        if pil.mode not in ("RGB", "L"):
            pil = pil.convert("RGB")
        elif pil.mode == "L":
            pil = pil.convert("RGB")
        rgb = np.asarray(pil)
        if rgb.ndim == 2:
            rgb = cv2.cvtColor(rgb, cv2.COLOR_GRAY2RGB)
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    except Exception:
        pass

    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image")
    return img


def rotate_bgr(img: np.ndarray, angle_cw: int) -> np.ndarray:
    """Rotate BGR image by 0/90/180/270 degrees clockwise."""
    angle_cw = int(angle_cw) % 360
    if angle_cw == 0:
        return img
    if angle_cw == 90:
        return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    if angle_cw == 180:
        return cv2.rotate(img, cv2.ROTATE_180)
    if angle_cw == 270:
        return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    raise ValueError(f"Unsupported rotation {angle_cw}")


def map_bbox_from_rotated(
    bbox: tuple[int, int, int, int],
    *,
    angle_cw: int,
    orig_w: int,
    orig_h: int,
) -> tuple[int, int, int, int] | None:
    """
    Map a bbox found on a clockwise-rotated copy back onto the original image.

    angle_cw: rotation applied to the original before detection (0/90/180/270).
    """
    angle_cw = int(angle_cw) % 360
    x1, y1, x2, y2 = bbox
    if angle_cw == 0:
        corners = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        xs = [c[0] for c in corners]
        ys = [c[1] for c in corners]
        return (
            int(np.clip(min(xs), 0, orig_w - 1)),
            int(np.clip(min(ys), 0, orig_h - 1)),
            int(np.clip(max(xs), 0, orig_w - 1)),
            int(np.clip(max(ys), 0, orig_h - 1)),
        )

    # Dimensions of the rotated canvas
    if angle_cw in (90, 270):
        rot_w, rot_h = orig_h, orig_w
    else:
        rot_w, rot_h = orig_w, orig_h

    def back(x: float, y: float) -> tuple[float, float]:
        if angle_cw == 90:
            # inverse of 90 CW = 90 CCW
            return y, rot_w - 1 - x
        if angle_cw == 180:
            return rot_w - 1 - x, rot_h - 1 - y
        if angle_cw == 270:
            # inverse of 270 CW = 90 CW
            return rot_h - 1 - y, x
        return x, y

    mapped = [back(x1, y1), back(x2, y1), back(x2, y2), back(x1, y2)]
    xs = [p[0] for p in mapped]
    ys = [p[1] for p in mapped]
    nx1 = int(np.clip(min(xs), 0, orig_w - 1))
    ny1 = int(np.clip(min(ys), 0, orig_h - 1))
    nx2 = int(np.clip(max(xs), 0, orig_w - 1))
    ny2 = int(np.clip(max(ys), 0, orig_h - 1))
    if nx2 <= nx1 or ny2 <= ny1:
        return None
    return (nx1, ny1, nx2, ny2)
