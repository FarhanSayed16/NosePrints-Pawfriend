"""Crop quality gate: coverage is optional for user-confirmed crops."""

import numpy as np

from app.services.quality import assess_crop_quality


def test_coverage_fails_on_tiny_nose_in_frame():
    crop = np.full((40, 40, 3), 80, dtype=np.uint8)
    result = assess_crop_quality(crop, (0, 0, 40, 40), 400, 400, check_coverage=True)
    assert result.nose_coverage < 0.15
    assert result.passed is False
    assert any("small" in issue.lower() for issue in result.issues)


def test_pre_cropped_skips_coverage_but_still_checks_blur():
    # Almost-flat crop → low Laplacian, should fail sharpness even without coverage.
    crop = np.full((80, 80, 3), 90, dtype=np.uint8)
    result = assess_crop_quality(crop, (0, 0, 80, 80), 80, 80, check_coverage=False)
    assert result.nose_coverage == 1.0
    assert any("blurry" in issue.lower() for issue in result.issues)
    assert result.passed is False
