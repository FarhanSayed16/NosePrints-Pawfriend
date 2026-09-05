"""G1 heuristics + capture gate tests (synthetic fixtures)."""

from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
import pytest
from fastapi import HTTPException

from app.schemas import QualityCheckResult
from app.services.capture_pipeline import prepare_nose_scan
from app.services.nose_detector import DetectionResult
from app.services.nose_heuristics import assess_nose_crop_heuristics, nose_likeness
from tests.fixtures_gen import ensure_fixtures


@pytest.fixture(scope="module")
def fixtures():
    return ensure_fixtures()


def _bgr_from_bytes(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    assert img is not None
    return img


def test_keyboard_fails_heuristics(fixtures):
    img = _bgr_from_bytes(fixtures["keyboard"].read_bytes())
    result = assess_nose_crop_heuristics(img, pre_cropped=True)
    assert result.passed is False
    joined = " ".join(result.issues).lower()
    assert "keyboard" in joined or "grid" in joined or "edges" in joined


def test_blank_wall_fails_likeness(fixtures):
    img = _bgr_from_bytes(fixtures["blank_wall"].read_bytes())
    result = assess_nose_crop_heuristics(img, pre_cropped=True)
    assert result.passed is False
    joined = " ".join(result.issues).lower()
    assert "blank" in joined or "flat" in joined or "leather" in joined or "look like" in joined


def test_nose_like_passes_heuristics(fixtures):
    img = _bgr_from_bytes(fixtures["nose_like"].read_bytes())
    result = assess_nose_crop_heuristics(img, pre_cropped=True)
    assert result.passed is True, result.issues
    assert nose_likeness(img) >= 0.32


def test_extreme_aspect_rejected():
    wide = np.full((40, 200, 3), 60, dtype=np.uint8)
    result = assess_nose_crop_heuristics(wide, pre_cropped=True)
    assert result.passed is False
    assert any("aspect" in i.lower() for i in result.issues)


def _ok_quality():
    return QualityCheckResult(
        passed=True,
        sharpness_score=200.0,
        brightness_score=90.0,
        nose_coverage=0.25,
        issues=[],
    )


def test_prepare_rejects_keyboard_via_heuristics_even_if_yolo_fires(fixtures):
    """G1.3: shared prepare_nose_scan blocks junk before embed/match."""
    data = fixtures["keyboard"].read_bytes()
    img = _bgr_from_bytes(data)
    h, w = img.shape[:2]
    fake = DetectionResult(
        original=img,
        crop=img.copy(),
        bbox=(10, 10, w - 10, h - 10),
        confidence=0.85,
    )
    with (
        patch("app.services.capture_pipeline.nose_detector") as det,
        patch("app.services.capture_pipeline.assess_crop_quality", return_value=_ok_quality()),
        patch("app.services.capture_pipeline.settings.DETECTOR_MIN_ACCEPT_CONF", 0.40),
        patch("app.services.capture_pipeline.settings.NOSE_REDETECT_ON_CROP", True),
    ):
        det.is_loaded = True
        det.detect.return_value = fake
        with pytest.raises(HTTPException) as exc:
            prepare_nose_scan(data, pre_cropped=True)
        assert exc.value.status_code == 422
        msg = exc.value.detail["message"].lower()
        assert "nose" in msg or "usable" in msg


def test_g0_no_nose_still_rejected_before_heuristics():
    detection = DetectionResult(
        original=np.full((80, 80, 3), 80, dtype=np.uint8),
        crop=None,
        bbox=None,
        confidence=0.0,
    )
    with patch("app.services.capture_pipeline.nose_detector") as det:
        det.is_loaded = True
        det.detect.return_value = detection
        with pytest.raises(HTTPException) as exc:
            prepare_nose_scan(b"x", pre_cropped=True)
        assert exc.value.status_code == 422
        assert "No dog nose" in exc.value.detail["message"]
