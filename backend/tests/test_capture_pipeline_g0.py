"""G0 capture gate: never accept missing/weak nose detections."""

from unittest.mock import patch

import numpy as np
import pytest
from fastapi import HTTPException

from app.schemas import QualityCheckResult
from app.services.capture_pipeline import prepare_nose_scan
from app.services.nose_detector import DetectionResult
from app.services.nose_heuristics import NoseGateResult


def _bgr(h=120, w=120, value=80):
    return np.full((h, w, 3), value, dtype=np.uint8)


def _pass_heuristics():
    return NoseGateResult(passed=True, issues=[], scores={})


def test_no_nose_rejected_even_when_pre_cropped():
    detection = DetectionResult(original=_bgr(), crop=None, bbox=None, confidence=0.0)
    with patch("app.services.capture_pipeline.nose_detector") as det:
        det.is_loaded = True
        det.detect.return_value = detection
        with pytest.raises(HTTPException) as exc:
            prepare_nose_scan(b"fake", pre_cropped=True)
        assert exc.value.status_code == 422
        assert "No dog nose" in exc.value.detail["message"]


def test_low_confidence_rejected():
    crop = _bgr(80, 80, 90)
    detection = DetectionResult(
        original=_bgr(200, 200),
        crop=crop,
        bbox=(40, 40, 120, 120),
        confidence=0.15,
    )
    with patch("app.services.capture_pipeline.nose_detector") as det:
        det.is_loaded = True
        det.detect.return_value = detection
        with patch("app.services.capture_pipeline.settings.DETECTOR_MIN_ACCEPT_CONF", 0.40):
            with pytest.raises(HTTPException) as exc:
                prepare_nose_scan(b"fake", pre_cropped=False)
            assert exc.value.status_code == 422
            assert "uncertain" in exc.value.detail["message"].lower()


def test_full_frame_bbox_rejected_on_scene_photo():
    """YOLO false hit covering almost the whole *scene* photo must 422."""
    frame = _bgr(894, 1200, 90)
    detection = DetectionResult(
        original=frame,
        crop=frame.copy(),
        bbox=(0, 0, 1200, 894),
        confidence=0.692,
    )
    with (
        patch("app.services.capture_pipeline.nose_detector") as det,
        patch("app.services.capture_pipeline.settings.DETECTOR_MIN_ACCEPT_CONF", 0.40),
        patch("app.services.capture_pipeline.settings.NOSE_MAX_BBOX_FRAME_FRACTION", 0.85),
        patch("app.services.capture_pipeline.settings.NOSE_REDETECT_ON_CROP", False),
    ):
        det.is_loaded = True
        det.detect.return_value = detection
        with pytest.raises(HTTPException) as exc:
            prepare_nose_scan(b"fake", pre_cropped=False)
        assert exc.value.status_code == 422
        detail = exc.value.detail
        joined = str(detail).lower()
        assert "whole photo" in joined or "almost" in joined or "usable" in joined


def test_pre_cropped_full_canvas_bbox_not_rejected_by_frame_rule():
    """Tight client crop: detector filling the crop canvas must not trip full-frame reject."""
    crop = _bgr(200, 200, 90)
    detection = DetectionResult(
        original=crop,
        crop=crop.copy(),
        bbox=(0, 0, 200, 200),
        confidence=0.72,
    )
    passed = QualityCheckResult(
        passed=True,
        sharpness_score=200.0,
        brightness_score=90.0,
        nose_coverage=0.5,
        issues=[],
    )
    with (
        patch("app.services.capture_pipeline.nose_detector") as det,
        patch("app.services.capture_pipeline.assess_crop_quality", return_value=passed),
        patch("app.services.capture_pipeline.assess_nose_crop_heuristics", return_value=_pass_heuristics()),
        patch("app.services.capture_pipeline.settings.DETECTOR_MIN_ACCEPT_CONF", 0.40),
        patch("app.services.capture_pipeline.settings.NOSE_REDETECT_ON_CROP", True),
        patch("app.services.capture_pipeline._redetect_on_crop", return_value=detection),
    ):
        det.is_loaded = True
        det.detect.return_value = detection
        scan = prepare_nose_scan(b"fake", pre_cropped=True)
        assert scan.crop is not None


def test_strong_detection_passes_gate():
    crop = _bgr(80, 80, 90)
    # Make crop look nose-like enough for heuristics
    crop = crop.copy()
    cv2 = __import__("cv2")
    cv2.ellipse(crop, (40, 40), (28, 24), 0, 0, 360, (30, 28, 26), -1)

    detection = DetectionResult(
        original=_bgr(200, 200),
        crop=crop,
        bbox=(40, 40, 120, 120),
        confidence=0.72,
    )
    second = DetectionResult(
        original=crop,
        crop=crop,
        bbox=(5, 5, 75, 75),
        confidence=0.70,
    )
    passed = QualityCheckResult(
        passed=True,
        sharpness_score=200.0,
        brightness_score=90.0,
        nose_coverage=0.2,
        issues=[],
    )
    with (
        patch("app.services.capture_pipeline.nose_detector") as det,
        patch("app.services.capture_pipeline.assess_crop_quality", return_value=passed),
        patch("app.services.capture_pipeline.assess_nose_crop_heuristics", return_value=_pass_heuristics()),
        patch("app.services.capture_pipeline.settings.DETECTOR_MIN_ACCEPT_CONF", 0.40),
        patch("app.services.capture_pipeline.settings.NOSE_REDETECT_ON_CROP", True),
    ):
        det.is_loaded = True
        det.detect.side_effect = [detection, second]
        scan = prepare_nose_scan(b"fake", pre_cropped=True)
        assert scan.confidence <= 0.72
        assert scan.crop is not None
