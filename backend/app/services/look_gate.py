"""
G3 soft gate for full-dog / face “look” photos (NOT biometric).

Warns on keyboard-like / blank junk that confuses staff side-by-side UI.
Callers may allow override (`force=true`) — look is optional context only.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from app.config import settings
from app.services.nose_heuristics import edge_density, grid_regularity


@dataclass
class LookGateResult:
    ok: bool
    soft_warn: bool
    issues: list[str]
    scores: dict[str, float]


def assess_look_photo(image_bytes: bytes) -> LookGateResult:
    if not image_bytes:
        return LookGateResult(False, False, ["Empty file"], {})

    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return LookGateResult(False, False, ["Could not decode image"], {})

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ed = edge_density(gray)
    grid = grid_regularity(gray)
    lap = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    aspect = float(w) / float(max(h, 1))

    scores = {
        "edge_density": round(ed, 4),
        "grid_regularity": round(grid, 4),
        "laplacian_var": round(lap, 2),
        "aspect_ratio": round(aspect, 4),
        "width": float(w),
        "height": float(h),
    }

    hard: list[str] = []
    soft: list[str] = []

    if min(h, w) < 64:
        hard.append("Photo is too small to be useful for staff comparison.")

    # Soft: junk that looks like keyboard / blank wall
    if ed >= settings.LOOK_MAX_EDGE_DENSITY and grid >= settings.LOOK_MAX_GRID_REGULARITY:
        soft.append(
            "This looks like a keyboard, screen, or grid — not a dog. Staff use this photo to compare coat and body."
        )
    elif ed >= settings.LOOK_MAX_EDGE_DENSITY:
        soft.append(
            "Very busy sharp edges — double-check this is a photo of the dog (body or face), not an object."
        )

    if lap < settings.LOOK_MIN_LAPLACIAN:
        soft.append("This looks almost blank/flat — take a clearer photo of the whole dog or face.")

    if hard:
        return LookGateResult(False, False, hard, scores)
    if soft:
        return LookGateResult(True, True, soft, scores)
    return LookGateResult(True, False, [], scores)
