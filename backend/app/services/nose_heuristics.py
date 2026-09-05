"""
G1 classical / geometric gates for nose crops.

These do not replace YOLO — they reject obvious junk (keyboards, blank walls,
extreme aspect ratios) before embeddings are written or matched.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from app.config import settings


@dataclass
class NoseGateResult:
    passed: bool
    issues: list[str]
    scores: dict[str, float]


def _aspect_ratio(h: int, w: int) -> float:
    return float(w) / float(max(h, 1))


def edge_density(gray: np.ndarray) -> float:
    """Fraction of strong Canny edges — keyboards / text score very high."""
    if gray.size == 0:
        return 1.0
    edges = cv2.Canny(gray, 80, 160)
    return float(np.mean(edges > 0))


def grid_regularity(gray: np.ndarray) -> float:
    """
    Rough keyboard/grill detector: strong periodic structure via FFT energy
    along axes. Returns 0–1 (higher = more grid-like).
    """
    h, w = gray.shape[:2]
    if h < 32 or w < 32:
        return 0.0
    small = cv2.resize(gray, (128, 128), interpolation=cv2.INTER_AREA)
    f = np.fft.fftshift(np.fft.fft2(small.astype(np.float32)))
    mag = np.abs(f)
    cy, cx = 64, 64
    mag[cy - 2 : cy + 3, cx - 2 : cx + 3] = 0  # drop DC
    # Energy near horizontal / vertical frequency bands
    band = 4
    horiz = float(np.sum(mag[cy - band : cy + band + 1, :]))
    vert = float(np.sum(mag[:, cx - band : cx + band + 1]))
    total = float(np.sum(mag)) + 1e-6
    return min(1.0, (horiz + vert) / total)


def nose_likeness(bgr: np.ndarray) -> float:
    """
    Lightweight “looks like nose leather” score in [0, 1].

    Real close-up noses tend to be:
    - darker in the center than the border (leather vs muzzle/background)
    - moderately textured (not flat wall, not ultra-edgey keyboard)
    """
    if bgr is None or bgr.size == 0:
        return 0.0
    h, w = bgr.shape[:2]
    if h < 16 or w < 16:
        return 0.0

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    # Center vs border brightness
    y0, y1 = int(h * 0.25), int(h * 0.75)
    x0, x1 = int(w * 0.25), int(w * 0.75)
    center = gray[y0:y1, x0:x1]
    border_mask = np.ones_like(gray, dtype=bool)
    border_mask[y0:y1, x0:x1] = False
    border = gray[border_mask]
    if center.size == 0 or border.size == 0:
        return 0.0

    c_mean = float(np.mean(center))
    b_mean = float(np.mean(border))
    # Prefer darker center (typical nose leather)
    dark_center = np.clip((b_mean - c_mean) / 80.0, -0.5, 1.0)
    dark_center = float((dark_center + 0.5) / 1.5)  # map to ~0–1

    # Mid texture (Laplacian) — wall too low, keyboard often very high
    lap = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if lap < 40:
        texture = lap / 40.0 * 0.5
    elif lap > 2000:
        texture = max(0.0, 1.0 - (lap - 2000) / 4000.0)
    else:
        texture = 0.55 + 0.45 * min(1.0, (lap - 40) / 800.0)

    ed = edge_density(gray)
    edge_ok = 1.0 - min(1.0, max(0.0, (ed - 0.12) / 0.35))

    score = 0.40 * dark_center + 0.35 * texture + 0.25 * edge_ok
    return float(np.clip(score, 0.0, 1.0))


def assess_nose_crop_heuristics(
    crop_bgr: np.ndarray,
    *,
    bbox: tuple[int, int, int, int] | None = None,
    frame_w: int | None = None,
    frame_h: int | None = None,
    pre_cropped: bool = False,
) -> NoseGateResult:
    """Geometric + classical checks on the final nose crop."""
    issues: list[str] = []
    if crop_bgr is None or crop_bgr.size == 0:
        return NoseGateResult(False, ["Empty nose crop"], {})

    h, w = crop_bgr.shape[:2]
    aspect = _aspect_ratio(h, w)
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    ed = edge_density(gray)
    grid = grid_regularity(gray)
    likeness = nose_likeness(crop_bgr)
    lap = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    scores = {
        "aspect_ratio": round(aspect, 4),
        "edge_density": round(ed, 4),
        "grid_regularity": round(grid, 4),
        "nose_likeness": round(likeness, 4),
        "laplacian_var": round(lap, 2),
        "crop_width": float(w),
        "crop_height": float(h),
    }

    min_ar = settings.NOSE_CROP_MIN_ASPECT
    max_ar = settings.NOSE_CROP_MAX_ASPECT
    if aspect < min_ar or aspect > max_ar:
        issues.append(
            f"Crop shape looks wrong for a nose (aspect {aspect:.2f}; "
            f"expected {min_ar:.2f}–{max_ar:.2f}). Tighten the box on the nose leather."
        )

    if lap < settings.NOSE_MIN_LAPLACIAN:
        issues.append(
            "Image is almost blank/flat — not a usable nose print. Retake a close-up of the nose."
        )

    if ed > settings.NOSE_MAX_EDGE_DENSITY:
        issues.append(
            "Too many sharp edges — this looks like a keyboard, screen, or busy object, not a nose."
        )

    # Grid alone can false-trigger on smooth ellipses; require elevated edges too (keyboards).
    if grid > settings.NOSE_MAX_GRID_REGULARITY and ed > 0.06:
        issues.append(
            "Image looks like a regular grid (keyboard/mesh). Upload a close-up of the dog's nose."
        )

    if likeness < settings.NOSE_MIN_LIKENESS:
        issues.append(
            f"Does not look like nose leather (score {likeness:.2f} < {settings.NOSE_MIN_LIKENESS:.2f}). "
            "Use a close-up of the black/pink nose, not the whole room or face."
        )

    # On full-frame detection, bbox should not be tiny or nearly the entire scene
    # when we still expect a focused nose (non-pre-cropped path checks coverage elsewhere).
    if bbox is not None and frame_w and frame_h and not pre_cropped:
        x1, y1, x2, y2 = bbox
        area = max(0, x2 - x1) * max(0, y2 - y1)
        frac = area / max(1, frame_w * frame_h)
        scores["bbox_frame_fraction"] = round(frac, 4)
        if frac > settings.NOSE_MAX_BBOX_FRAME_FRACTION:
            issues.append(
                "Detected region covers almost the whole photo — move closer so the nose fills the guide."
            )

    # For client crops, the detector box inside the crop should occupy a real share of it
    if bbox is not None and pre_cropped:
        x1, y1, x2, y2 = bbox
        area = max(0, x2 - x1) * max(0, y2 - y1)
        frac = area / max(1, h * w)
        scores["bbox_crop_fraction"] = round(frac, 4)
        if frac < settings.NOSE_MIN_BBOX_IN_CROP:
            issues.append(
                "Nose region is only a tiny part of your crop — enlarge the box onto the nose leather."
            )

    return NoseGateResult(passed=len(issues) == 0, issues=issues, scores=scores)


def encode_bgr_jpeg(bgr: np.ndarray, quality: int = 95) -> bytes:
    ok, buf = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise ValueError("Could not encode crop JPEG")
    return buf.tobytes()
