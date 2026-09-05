"""
G3 soft gate for full-dog / face “look” photos (NOT biometric).

Warns on keyboard-like / blank / screen UI junk that confuses staff side-by-side UI.
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


def screen_ui_score(bgr: np.ndarray) -> float:
    """
    Score [0,1] for phone/laptop UI screenshots (chat bubbles, UI greens, flat panels).
    Real outdoor dog photos score low.
    """
    if bgr is None or bgr.size == 0:
        return 0.0
    h, w = bgr.shape[:2]
    if h < 32 or w < 32:
        return 0.0

    # Downscale for speed
    small = cv2.resize(bgr, (160, 120), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    hch, sch, vch = cv2.split(hsv)

    # WhatsApp / Material-ish green chat bubbles
    green = (
        (hch >= 35)
        & (hch <= 95)
        & (sch >= 60)
        & (vch >= 60)
    )
    green_frac = float(np.mean(green))

    # Highly saturated “UI chrome” (icons, bubbles, accent bars)
    sat_frac = float(np.mean(sch > 90))

    # Large near-uniform panels (chat wallpaper / app chrome)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    lap = float(cv2.Laplacian(blur, cv2.CV_64F).var())
    # Low local variance regions
    local = cv2.blur(gray.astype(np.float32) ** 2, (9, 9)) - cv2.blur(gray.astype(np.float32), (9, 9)) ** 2
    flat_frac = float(np.mean(local < 80))

    # Strong horizontal structure (status bars / message rows)
    edges = cv2.Canny(gray, 50, 120)
    row_energy = np.mean(edges, axis=1)
    horiz_lines = float(np.mean(row_energy > 0.08))

    score = (
        0.35 * min(1.0, green_frac / 0.12)
        + 0.25 * min(1.0, sat_frac / 0.28)
        + 0.20 * flat_frac
        + 0.20 * horiz_lines
    )
    # Blank walls are flat but low sat / no green — don't inflate
    if sat_frac < 0.04 and green_frac < 0.01:
        score *= 0.35
    if lap > 900 and green_frac < 0.02:
        # Busy real-world photo
        score *= 0.5
    return float(np.clip(score, 0.0, 1.0))


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
    ui = screen_ui_score(img)

    scores = {
        "edge_density": round(ed, 4),
        "grid_regularity": round(grid, 4),
        "laplacian_var": round(lap, 2),
        "aspect_ratio": round(aspect, 4),
        "screen_ui_score": round(ui, 4),
        "width": float(w),
        "height": float(h),
    }

    hard: list[str] = []
    soft: list[str] = []

    if min(h, w) < 64:
        hard.append("Photo is too small to be useful for staff comparison.")

    # Soft: phone/laptop UI (chat screens, desktops) — common demo junk
    if ui >= settings.LOOK_MAX_SCREEN_UI:
        soft.append(
            "This looks like a phone or laptop screen, not a dog. Staff need a body or face photo of the dog."
        )

    # Soft: junk that looks like keyboard / blank wall / busy screen
    if ed >= settings.LOOK_MAX_EDGE_DENSITY and grid >= settings.LOOK_MAX_GRID_REGULARITY:
        soft.append(
            "This looks like a keyboard, screen, or grid — not a dog. Staff use this photo to compare coat and body."
        )
    elif ed >= settings.LOOK_MAX_EDGE_DENSITY:
        soft.append(
            "Very busy sharp edges — double-check this is a photo of the dog (body or face), not an object."
        )
    elif ed >= settings.LOOK_MAX_EDGE_DENSITY * 0.55 and lap > 350:
        soft.append(
            "This may be a phone/laptop screen or busy object — use a real photo of the dog’s body or face."
        )

    if lap < settings.LOOK_MIN_LAPLACIAN:
        soft.append("This looks almost blank/flat — take a clearer photo of the whole dog or face.")

    if hard:
        return LookGateResult(False, False, hard, scores)
    if soft:
        return LookGateResult(True, True, soft, scores)
    return LookGateResult(True, False, [], scores)
