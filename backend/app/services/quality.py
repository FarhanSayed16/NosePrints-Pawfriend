"""
Image quality assessment service.
Checks sharpness, brightness, and nose coverage before accepting a scan.
"""

import cv2
import numpy as np
from app.config import settings
from app.schemas import QualityCheckResult


def assess_image_quality(
    image_bytes: bytes,
    nose_bbox: tuple[int, int, int, int] | None = None,
    frame_width: int | None = None,
    frame_height: int | None = None,
) -> QualityCheckResult:
    """
    Run quality checks on a nose-print image.

    Args:
        image_bytes: Raw image bytes (JPEG/PNG)
        nose_bbox: (x1, y1, x2, y2) bounding box of detected nose region
        frame_width: Original frame width (for coverage calculation)
        frame_height: Original frame height (for coverage calculation)

    Returns:
        QualityCheckResult with pass/fail and detailed scores
    """
    # Decode image
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

    issues = []

    # ── 1. Sharpness (Laplacian variance) ──
    # Standard blur-detection method used in the published research itself
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    sharpness_score = float(laplacian_var)

    if sharpness_score < settings.MIN_SHARPNESS_SCORE:
        issues.append(f"Image too blurry (sharpness: {sharpness_score:.1f}, minimum: {settings.MIN_SHARPNESS_SCORE})")

    # ── 2. Brightness (mean pixel intensity) ──
    mean_brightness = float(np.mean(gray))
    brightness_score = mean_brightness

    if mean_brightness < settings.MIN_BRIGHTNESS:
        issues.append(f"Image too dark (brightness: {mean_brightness:.0f}, minimum: {settings.MIN_BRIGHTNESS})")
    elif mean_brightness > settings.MAX_BRIGHTNESS:
        issues.append(f"Image too bright/washed out (brightness: {mean_brightness:.0f}, maximum: {settings.MAX_BRIGHTNESS})")

    # ── 3. Nose coverage (nose bbox area vs frame area) ──
    nose_coverage = 0.0
    if nose_bbox and frame_width and frame_height:
        x1, y1, x2, y2 = nose_bbox
        nose_area = (x2 - x1) * (y2 - y1)
        frame_area = frame_width * frame_height
        nose_coverage = nose_area / frame_area if frame_area > 0 else 0.0

        if nose_coverage < settings.MIN_NOSE_COVERAGE:
            issues.append(
                f"Nose too small in frame ({nose_coverage:.1%} coverage, minimum: {settings.MIN_NOSE_COVERAGE:.0%}). "
                "Move closer to the dog."
            )
    else:
        # If no bbox provided, skip coverage check
        nose_coverage = -1.0  # Indicates not checked

    passed = len(issues) == 0

    return QualityCheckResult(
        passed=passed,
        sharpness_score=sharpness_score,
        brightness_score=brightness_score,
        nose_coverage=nose_coverage,
        issues=issues,
    )
