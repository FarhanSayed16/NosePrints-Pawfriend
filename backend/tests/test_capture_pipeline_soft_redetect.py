"""Soft re-detect fallback: tight client crops must not fail when YOLO misses pass 2."""

from unittest.mock import patch

import cv2
import numpy as np
from fastapi import HTTPException

from app.schemas import QualityCheckResult
from app.services.capture_pipeline import prepare_nose_scan
from app.services.nose_detector import DetectionResult
from app.services.nose_heuristics import NoseGateResult


def _nose_like(size=160):
    img = np.full((size, size, 3), 150, dtype=np.uint8)
    cv2.ellipse(img, (size // 2, size // 2), (55, 48), 0, 0, 360, (28, 24, 22), -1)
    return img


def _pass_heuristics():
    return NoseGateResult(passed=True, issues=[], scores={"nose_likeness": 0.7})


def test_pre_cropped_yolo_miss_accepts_likeness_canvas():
    crop = _nose_like()
    empty = DetectionResult(original=crop, crop=None, bbox=None, confidence=0.0)
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
        patch("app.services.capture_pipeline.settings.NOSE_REDETECT_ON_CROP", True),
        patch("app.services.capture_pipeline.settings.NOSE_REDETECT_SOFT_FALLBACK", True),
        patch("app.services.capture_pipeline.settings.DETECTOR_MIN_ACCEPT_CONF", 0.28),
        patch(
            "app.services.capture_pipeline._redetect_on_crop",
            return_value=DetectionResult(original=crop, crop=None, bbox=None, confidence=0.0),
        ),
    ):
        det.is_loaded = True
        det.detect.return_value = empty
        scan = prepare_nose_scan(b"fake", pre_cropped=True)
        assert scan.crop is not None


def test_pre_cropped_second_pass_miss_keeps_first():
    crop = _nose_like()
    first = DetectionResult(
        original=crop,
        crop=crop.copy(),
        bbox=(10, 10, 150, 150),
        confidence=0.55,
    )
    miss = DetectionResult(original=crop, crop=None, bbox=None, confidence=0.05)
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
        patch("app.services.capture_pipeline.settings.NOSE_REDETECT_ON_CROP", True),
        patch("app.services.capture_pipeline.settings.NOSE_REDETECT_SOFT_FALLBACK", True),
        patch("app.services.capture_pipeline.settings.DETECTOR_MIN_ACCEPT_CONF", 0.28),
        patch("app.services.capture_pipeline._redetect_on_crop", return_value=miss),
    ):
        det.is_loaded = True
        det.detect.return_value = first
        scan = prepare_nose_scan(b"fake", pre_cropped=True)
        assert scan.crop is not None
        assert scan.confidence >= 0.5


def test_pre_cropped_junk_still_rejected():
    junk = np.full((120, 120, 3), 200, dtype=np.uint8)
    empty = DetectionResult(original=junk, crop=None, bbox=None, confidence=0.0)
    fail = NoseGateResult(passed=False, issues=["not a nose"], scores={})
    with (
        patch("app.services.capture_pipeline.nose_detector") as det,
        patch("app.services.capture_pipeline.assess_nose_crop_heuristics", return_value=fail),
        patch("app.services.capture_pipeline.settings.NOSE_REDETECT_ON_CROP", True),
    ):
        det.is_loaded = True
        det.detect.return_value = empty
        try:
            prepare_nose_scan(b"fake", pre_cropped=True)
            assert False, "expected HTTPException"
        except HTTPException as exc:
            assert exc.status_code == 422
