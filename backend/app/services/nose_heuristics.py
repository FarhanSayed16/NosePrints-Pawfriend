"""
G1 classical / geometric gates for nose crops.

These do not replace YOLO — they reject obvious junk (keyboards, blank walls,
fabric blankets, colourful screens, extreme aspect ratios) before embeddings
are written or matched.
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


def colorfulness(bgr: np.ndarray) -> float:
    """
    Hasler–Süsstrunk colorfulness. Nose leather is low; printed fabric / UI
    screens / rainbow blankets score high.
    """
    if bgr is None or bgr.size == 0:
        return 0.0
    b, g, r = cv2.split(bgr.astype(np.float32))
    rg = np.abs(r - g)
    yb = np.abs(0.5 * (r + g) - b)
    return float(
        np.sqrt(rg.std() ** 2 + yb.std() ** 2)
        + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2)
    )


def hue_spread_degrees(bgr: np.ndarray) -> float:
    """
    Circular std-dev of hue (degrees) on mid-bright, saturated pixels.
    Multi-colour fabric spreads widely; dark leather clusters tightly.
    """
    if bgr is None or bgr.size == 0:
        return 0.0
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    mask = (s > 35) & (v > 40) & (v < 245)
    if int(np.count_nonzero(mask)) < 40:
        return 0.0
    # Hue is 0–179 in OpenCV; map to radians on a circle
    angles = h[mask].astype(np.float64) * (2.0 * np.pi / 180.0)
    mean_c = np.mean(np.cos(angles))
    mean_s = np.mean(np.sin(angles))
    r = float(np.hypot(mean_c, mean_s))
    r = min(1.0, max(0.0, r))
    # Circular std ≈ sqrt(-2 ln R) in radians → degrees
    if r < 1e-6:
        return 90.0
    std_rad = float(np.sqrt(max(0.0, -2.0 * np.log(r))))
    return float(np.degrees(std_rad))


def dark_center_score(gray: np.ndarray) -> float:
    """Prefer darker center than border (typical black nose leather). Returns ~0–1."""
    h, w = gray.shape[:2]
    if h < 16 or w < 16:
        return 0.0
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
    dark_center = np.clip((b_mean - c_mean) / 80.0, -0.5, 1.0)
    return float((dark_center + 0.5) / 1.5)


def pink_leather_score(bgr: np.ndarray) -> float:
    """
    Pink / light-brown nose leather is often *brighter* in the center than the
    muzzle — dark_center alone would reject these. Score warm, low-neon centers
    that are brighter than the border (not uniform fur).
    """
    if bgr is None or bgr.size == 0:
        return 0.0
    h, w = bgr.shape[:2]
    if h < 16 or w < 16:
        return 0.0
    y0, y1 = int(h * 0.25), int(h * 0.75)
    x0, x1 = int(w * 0.25), int(w * 0.75)
    center = bgr[y0:y1, x0:x1]
    if center.size == 0:
        return 0.0
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    c_mean = float(np.mean(gray[y0:y1, x0:x1]))
    border_mask = np.ones_like(gray, dtype=bool)
    border_mask[y0:y1, x0:x1] = False
    b_mean = float(np.mean(gray[border_mask]))
    # Pink leather: center should be brighter than muzzle/border
    if c_mean < b_mean + 6:
        return 0.0

    hsv = cv2.cvtColor(center, cv2.COLOR_BGR2HSV)
    hh, ss, vv = cv2.split(hsv)
    mean_h = float(np.mean(hh))
    mean_s = float(np.mean(ss))
    mean_v = float(np.mean(vv))
    # OpenCV hue: red/pink wraps ~0–15 and ~160–179; brown ~8–25
    warm_hue = mean_h <= 28 or mean_h >= 155
    if not warm_hue:
        return 0.0
    if mean_s > 140 or mean_v < 35 or mean_v > 230:
        return 0.0  # neon dye or washed out
    sat_ok = 1.0 - min(1.0, max(0.0, (mean_s - 40.0) / 120.0))
    return float(np.clip(0.45 + 0.40 * sat_ok, 0.0, 1.0))


def leather_center_score(bgr: np.ndarray) -> float:
    """Best of dark-center (black noses) and pink/brown leather cue."""
    if bgr is None or bgr.size == 0:
        return 0.0
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return float(max(dark_center_score(gray), pink_leather_score(bgr)))


def human_skin_score(bgr: np.ndarray) -> float:
    """
    Fraction of *center* pixels that look like human skin (YCrCb ∩ HSV peach).
    High on human faces/noses; near 0 on black dog leather. Intersection avoids
    flagging gray/tan muzzle fur that alone matches a loose YCrCb skin range.
    """
    if bgr is None or bgr.size == 0:
        return 0.0
    h, w = bgr.shape[:2]
    if h < 16 or w < 16:
        return 0.0
    y0, y1 = int(h * 0.20), int(h * 0.80)
    x0, x1 = int(w * 0.20), int(w * 0.80)
    center = bgr[y0:y1, x0:x1]
    if center.size == 0:
        return 0.0
    ycrcb = cv2.cvtColor(center, cv2.COLOR_BGR2YCrCb)
    skin_y = cv2.inRange(ycrcb, (40, 135, 85), (245, 170, 125))
    hsv = cv2.cvtColor(center, cv2.COLOR_BGR2HSV)
    # Require real chroma so gray fur does not count as skin
    skin_h = cv2.inRange(hsv, (0, 45, 70), (22, 155, 245))
    skin = cv2.bitwise_and(skin_y, skin_h)
    return float(np.mean(skin > 0))


def nose_likeness(bgr: np.ndarray) -> float:
    """
    Lightweight “looks like nose leather” score in [0, 1].

    Real close-up noses tend to be:
    - darker *or* warm pink/brown in the center
    - moderately textured (not flat wall, not ultra-edgey keyboard)
    - low colorfulness
    """
    if bgr is None or bgr.size == 0:
        return 0.0
    h, w = bgr.shape[:2]
    if h < 16 or w < 16:
        return 0.0

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    center_ok = leather_center_score(bgr)

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

    cf = colorfulness(bgr)
    colour_ok = 1.0 - min(1.0, max(0.0, (cf - 12.0) / 40.0))

    score = (
        0.38 * center_ok
        + 0.28 * texture
        + 0.20 * edge_ok
        + 0.14 * colour_ok
    )
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
    cf = colorfulness(crop_bgr)
    hue_std = hue_spread_degrees(crop_bgr)
    dark_c = leather_center_score(crop_bgr)
    skin = human_skin_score(crop_bgr)

    scores = {
        "aspect_ratio": round(aspect, 4),
        "edge_density": round(ed, 4),
        "grid_regularity": round(grid, 4),
        "nose_likeness": round(likeness, 4),
        "laplacian_var": round(lap, 2),
        "colorfulness": round(cf, 2),
        "hue_spread_deg": round(hue_std, 2),
        "dark_center": round(dark_c, 4),
        "human_skin": round(skin, 4),
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

    if cf > settings.NOSE_MAX_COLORFULNESS:
        issues.append(
            "Too colourful for nose leather — this looks like fabric, a screen, or a patterned object. "
            "Crop only the black/pink nose."
        )

    if hue_std > settings.NOSE_MAX_HUE_SPREAD:
        issues.append(
            "Too many different colours in the crop — use a tight box on the nose leather only, "
            "not a blanket, coat, or busy background."
        )

    if dark_c < settings.NOSE_MIN_DARK_CENTER:
        issues.append(
            "Crop does not look like nose leather in the center (dark or pink/brown). "
            "Tighten the box on the nose — not fur, the body, or the floor."
        )

    # Reject human faces / skin-dominant crops (not a dog nose print)
    if skin >= settings.NOSE_MAX_HUMAN_SKIN and dark_c < settings.NOSE_MIN_DARK_CENTER + 0.08:
        issues.append(
            "This looks like human skin or a human nose, not a dog nose print. "
            "Photograph only the dog's black/pink nose leather."
        )
    elif skin >= settings.NOSE_MAX_HUMAN_SKIN * 1.15 and likeness < settings.NOSE_MIN_LIKENESS + 0.12:
        issues.append(
            "Too much skin tone for a dog nose crop. Use only the dog's nose leather."
        )

    if likeness < settings.NOSE_MIN_LIKENESS:
        issues.append(
            f"Does not look like nose leather (score {likeness:.2f} < {settings.NOSE_MIN_LIKENESS:.2f}). "
            "Use a close-up of the black/pink nose, not fur, blankets, or the whole room."
        )

    # Scene photos only: bbox must not cover almost the entire frame.
    # On pre_cropped client crops, a good nose often fills most of the canvas — do not max-reject.
    if bbox is not None and frame_w and frame_h and not pre_cropped:
        x1, y1, x2, y2 = bbox
        area = max(0, x2 - x1) * max(0, y2 - y1)
        frac = area / max(1, frame_w * frame_h)
        scores["bbox_frame_fraction"] = round(frac, 4)
        if frac > settings.NOSE_MAX_BBOX_FRAME_FRACTION:
            issues.append(
                "Detected region covers almost the whole photo — that is not a nose crop. "
                "Tighten the box onto the black/pink nose leather only."
            )

    # Client crops: re-detect box must be a real share of the canvas (not a speck,
    # and not a near-full-frame YOLO false hit unless the box is the soft-miss canvas).
    if bbox is not None and pre_cropped:
        x1, y1, x2, y2 = bbox
        area = max(0, x2 - x1) * max(0, y2 - y1)
        frac = area / max(1, h * w)
        scores["bbox_crop_fraction"] = round(frac, 4)
        if frac < settings.NOSE_MIN_BBOX_IN_CROP:
            issues.append(
                "Nose region is only a tiny part of your crop — enlarge the box onto the nose leather."
            )
        full_canvas = x1 <= 2 and y1 <= 2 and x2 >= w - 2 and y2 >= h - 2
        if (
            not full_canvas
            and frac > settings.NOSE_MAX_BBOX_IN_CROP
            and float(scores.get("nose_likeness", 0)) < settings.NOSE_MIN_LIKENESS + 0.08
        ):
            issues.append(
                "Detected region covers almost the whole crop without looking like nose leather. "
                "Tighten the box onto the dog's nose only."
            )

    return NoseGateResult(passed=len(issues) == 0, issues=issues, scores=scores)


def encode_bgr_jpeg(bgr: np.ndarray, quality: int = 95) -> bytes:
    ok, buf = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise ValueError("Could not encode crop JPEG")
    return buf.tobytes()


def suggest_nose_bbox_norm(
    bgr: np.ndarray,
    *,
    dog_bbox: tuple[int, int, int, int] | None = None,
) -> dict[str, float] | None:
    """
    When YOLO finds nothing on a phone face/body photo, suggest a starting box
    on the darkest compact window in the face band (nose leather).

    If dog_bbox is set (Stage-1 COCO dog), search only the upper portion of that
    box so paws/pavement cannot win. Returns normalized {x1,y1,x2,y2} or None.
    """
    if bgr is None or bgr.size == 0:
        return None
    h, w = bgr.shape[:2]
    if min(h, w) < 64:
        return None

    gray_full = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    # Skip junk gate when we already know there is a dog in-frame
    if dog_bbox is None:
        if edge_density(gray_full) >= settings.LOOK_MAX_EDGE_DENSITY * 0.9:
            return None
        if (
            grid_regularity(gray_full) >= settings.LOOK_MAX_GRID_REGULARITY
            and edge_density(gray_full) > 0.05
        ):
            return None

    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    _hch, sch, vch = cv2.split(hsv)
    v = vch.astype(np.float32)

    # Default: central face band. With dog box: upper-middle of the dog.
    if dog_bbox is not None:
        dx1, dy1, dx2, dy2 = dog_bbox
        dx1, dy1 = max(0, dx1), max(0, dy1)
        dx2, dy2 = min(w, dx2), min(h, dy2)
        bh = max(1, dy2 - dy1)
        bw = max(1, dx2 - dx1)
        # Upper 55% of dog box, inset horizontally
        y0 = dy1 + int(bh * 0.05)
        y1 = dy1 + int(bh * 0.55)
        x0 = dx1 + int(bw * 0.15)
        x1 = dx2 - int(bw * 0.15)
    else:
        y0, y1 = int(h * 0.18), int(h * 0.78)
        x0, x1 = int(w * 0.22), int(w * 0.78)
    if y1 - y0 < 40 or x1 - x0 < 40:
        if dog_bbox is not None:
            dx1, dy1, dx2, dy2 = dog_bbox
            cx = (dx1 + dx2) / 2 / w
            cy = (dy1 + 0.35 * (dy2 - dy1)) / h
            side = 0.14
            return {
                "x1": float(np.clip(cx - side / 2, 0.02, 0.85)),
                "y1": float(np.clip(cy - side / 2, 0.02, 0.85)),
                "x2": float(np.clip(cx + side / 2, 0.10, 0.98)),
                "y2": float(np.clip(cy + side / 2, 0.10, 0.98)),
            }
        return {"x1": 0.38, "y1": 0.30, "x2": 0.62, "y2": 0.54}

    edge = float(min(h, w))
    # Edge penalty: whiskers/crevices are high-Canny; smooth leather stays dark
    edges = cv2.Canny(gray_full, 40, 120)
    edges_dilated = cv2.dilate(edges, np.ones((3, 3), np.uint8))
    v_penalized = cv2.add(v, edges_dilated.astype(np.float32) * 0.6)

    # Multi-scale darkest mean window — black leather wins over whiskers / shade
    win_fracs = (0.10, 0.13, 0.16, 0.20)
    best: tuple[float, int, int, int] | None = None  # meanV, cx, cy, win
    for frac in win_fracs:
        win = max(24, int(round(edge * frac)))
        if win % 2 == 0:
            win += 1
        blur = cv2.boxFilter(v_penalized, -1, (win, win), normalize=True)
        region = blur[y0:y1, x0:x1]
        min_val, _, min_loc, _ = cv2.minMaxLoc(region)
        cx = int(min_loc[0] + x0)
        cy = int(min_loc[1] + y0)
        # Prefer truly dark leather; skip mid-gray pavement (threshold on penalized V)
        if min_val > 110:
            continue
        # Soft center bias so ear shadows on the side lose to a true nose
        center_pen = 1.0 + 0.35 * (((cx / w) - 0.5) ** 2 / 0.08)
        score = float(min_val) * center_pen
        if best is None or score < best[0]:
            best = (score, cx, cy, win)

    if best is None:
        # Pink noses: look for low-V moderate-S patches instead of failing open
        pink = ((vch < 150) & (vch > 45) & (sch > 30) & (sch < 160)).astype(np.uint8) * 255
        pink = cv2.morphologyEx(pink, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        if int(np.count_nonzero(pink[y0:y1, x0:x1])) < 80:
            return {"x1": 0.38, "y1": 0.30, "x2": 0.62, "y2": 0.54}
        heat = cv2.GaussianBlur(pink.astype(np.float32), (31, 31), 0)
        _, _, _, max_loc = cv2.minMaxLoc(heat[y0:y1, x0:x1])
        cx = int(max_loc[0] + x0)
        cy = int(max_loc[1] + y0)
        win = max(24, int(round(edge * 0.14)))
    else:
        _score, cx, cy, win = best

    # Box slightly larger than the dark window so leather fills most of it
    side = win * 1.35
    side = float(np.clip(side, edge * 0.10, edge * 0.26))
    x1n = (cx - side / 2) / w
    x2n = (cx + side / 2) / w
    y1n = (cy - side / 2) / h
    y2n = (cy + side / 2) / h
    x1n = float(np.clip(x1n, 0.02, 0.85))
    y1n = float(np.clip(y1n, 0.02, 0.85))
    x2n = float(np.clip(max(x2n, x1n + 0.08), 0.10, 0.98))
    y2n = float(np.clip(max(y2n, y1n + 0.08), 0.10, 0.98))
    return {"x1": x1n, "y1": y1n, "x2": x2n, "y2": y2n}
