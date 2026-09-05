"""
Image quality assessment — sharpness/brightness on the **cropped nose**,
coverage against the original frame.
"""

import cv2
import numpy as np

from app.config import settings
from app.schemas import QualityCheckResult


def _scores_from_bgr(img: np.ndarray) -> tuple[float, float]:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(np.mean(gray))
    return sharpness, brightness


def assess_crop_quality(
    crop_bgr: np.ndarray,
    nose_bbox: tuple[int, int, int, int],
    frame_width: int,
    frame_height: int,
    *,
    check_coverage: bool = True,
) -> QualityCheckResult:
    """Quality gate for a detected nose crop."""
    issues: list[str] = []
    sharpness_score, brightness_score = _scores_from_bgr(crop_bgr)
    min_sharp = (
        settings.MIN_SHARPNESS_SCORE
        if check_coverage
        else settings.MIN_SHARPNESS_SCORE_CROP
    )

    if sharpness_score < min_sharp:
        issues.append(
            f"Nose crop too blurry (sharpness: {sharpness_score:.1f}, "
            f"minimum: {min_sharp}). Hold steady and get closer to the nose leather."
        )

    if brightness_score < settings.MIN_BRIGHTNESS:
        issues.append(
            f"Nose too dark (brightness: {brightness_score:.0f}, "
            f"minimum: {settings.MIN_BRIGHTNESS}). Add light."
        )
    elif brightness_score > settings.MAX_BRIGHTNESS:
        issues.append(
            f"Nose too bright/washed out (brightness: {brightness_score:.0f}, "
            f"maximum: {settings.MAX_BRIGHTNESS})."
        )

    x1, y1, x2, y2 = nose_bbox
    nose_area = max(0, x2 - x1) * max(0, y2 - y1)
    frame_area = max(1, frame_width * frame_height)
    nose_coverage = nose_area / frame_area
    if check_coverage and nose_coverage < settings.MIN_NOSE_COVERAGE:
        issues.append(
            f"Nose too small in frame ({nose_coverage:.1%} coverage, "
            f"minimum: {settings.MIN_NOSE_COVERAGE:.0%}). Move closer."
        )

    return QualityCheckResult(
        passed=len(issues) == 0,
        sharpness_score=sharpness_score,
        brightness_score=brightness_score,
        nose_coverage=nose_coverage,
        issues=issues,
    )


def assess_image_quality(
    image_bytes: bytes,
    nose_bbox: tuple[int, int, int, int] | None = None,
    frame_width: int | None = None,
    frame_height: int | None = None,
) -> QualityCheckResult:
    """
    Backward-compatible helper. Prefer assess_crop_quality once a bbox exists.
    If a bbox is given, sharpness/brightness still run on the crop region.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return QualityCheckResult(
            passed=False,
            sharpness_score=0.0,
            brightness_score=0.0,
            nose_coverage=0.0,
            issues=["Could not decode image"],
        )

    h, w = img.shape[:2]
    if nose_bbox:
        x1, y1, x2, y2 = nose_bbox
        crop = img[max(0, y1) : min(h, y2), max(0, x1) : min(w, x2)]
        if crop.size == 0:
            return QualityCheckResult(
                passed=False,
                sharpness_score=0.0,
                brightness_score=0.0,
                nose_coverage=0.0,
                issues=["Nose crop was empty"],
            )
        return assess_crop_quality(
            crop,
            nose_bbox,
            frame_width or w,
            frame_height or h,
            check_coverage=True,
        )

    issues: list[str] = []
    sharpness_score, brightness_score = _scores_from_bgr(img)
    if sharpness_score < settings.MIN_SHARPNESS_SCORE:
        issues.append(
            f"Image too blurry (sharpness: {sharpness_score:.1f}, "
            f"minimum: {settings.MIN_SHARPNESS_SCORE})"
        )
    if brightness_score < settings.MIN_BRIGHTNESS:
        issues.append(f"Image too dark (brightness: {brightness_score:.0f})")
    elif brightness_score > settings.MAX_BRIGHTNESS:
        issues.append(f"Image too bright (brightness: {brightness_score:.0f})")

    return QualityCheckResult(
        passed=len(issues) == 0,
        sharpness_score=sharpness_score,
        brightness_score=brightness_score,
        nose_coverage=-1.0,
        issues=issues,
    )
