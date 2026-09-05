"""Detect-preview honesty — never report Nose found on junk / full-frame hits."""

from unittest.mock import MagicMock, patch

import cv2
import numpy as np
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.matching import router as matching_router
from app.services.nose_heuristics import NoseGateResult, assess_nose_crop_heuristics
from app.services.nose_detector import DetectionResult
from tests.fixtures_gen import ensure_fixtures


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(matching_router, prefix="/api/v1")
    return TestClient(app)


def _detection(img: np.ndarray, bbox, conf: float) -> DetectionResult:
    x1, y1, x2, y2 = bbox
    crop = img[y1:y2, x1:x2].copy() if bbox else None
    return DetectionResult(
        original=img,
        crop=crop,
        bbox=bbox,
        confidence=conf,
    )


def test_detect_preview_keyboard_not_detected():
    fixtures = ensure_fixtures()
    data = fixtures["keyboard"].read_bytes()
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    # YOLO-style false hit covering almost the whole frame
    fake = _detection(img, (0, 0, w, h), 0.85)

    mock_det = MagicMock()
    mock_det.is_loaded = True
    mock_det.detect.return_value = fake

    with patch("app.routers.matching.nose_detector", mock_det):
        res = _client().post(
            "/api/v1/match/detect-preview",
            files={"file": ("keyboard.jpg", data, "image/jpeg")},
        )
    assert res.status_code == 200
    body = res.json()
    assert body["detected"] is False
    assert body["bbox"] is None
    assert "nose found" not in (body.get("message") or "").lower()


def test_detect_preview_uncertain_still_suggests_bbox():
    """Soft heuristic miss / mid conf should still return a box to drag."""
    fixtures = ensure_fixtures()
    data = fixtures["nose_like"].read_bytes()
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    bx, by = int(w * 0.25), int(h * 0.25)
    fake = _detection(img, (bx, by, bx + int(w * 0.45), by + int(h * 0.45)), 0.34)

    mock_det = MagicMock()
    mock_det.is_loaded = True
    mock_det.detect.return_value = fake

    with (
        patch("app.routers.matching.nose_detector", mock_det),
        patch(
            "app.services.nose_heuristics.assess_nose_crop_heuristics",
            return_value=NoseGateResult(
                passed=False,
                issues=["soft miss"],
                scores={
                    "edge_density": 0.05,
                    "grid_regularity": 0.1,
                    "colorfulness": 8.0,
                    "hue_spread_deg": 10.0,
                },
            ),
        ),
    ):
        res = _client().post(
            "/api/v1/match/detect-preview",
            files={"file": ("nose.jpg", data, "image/jpeg")},
        )
    assert res.status_code == 200
    body = res.json()
    assert body["detected"] is False
    assert body["bbox"] is not None
    assert body["bbox"]["x2"] > body["bbox"]["x1"]
    assert "nose found" not in (body.get("message") or "").lower()


def test_detect_preview_low_conf_not_detected():
    fixtures = ensure_fixtures()
    data = fixtures["nose_like"].read_bytes()
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    # Tight box but very low confidence
    bx = int(w * 0.3)
    by = int(h * 0.3)
    fake = _detection(img, (bx, by, bx + int(w * 0.35), by + int(h * 0.35)), 0.15)

    mock_det = MagicMock()
    mock_det.is_loaded = True
    mock_det.detect.return_value = fake

    with patch("app.routers.matching.nose_detector", mock_det):
        res = _client().post(
            "/api/v1/match/detect-preview",
            files={"file": ("nose.jpg", data, "image/jpeg")},
        )
    assert res.status_code == 200
    body = res.json()
    assert body["detected"] is False
    assert "nose found" not in (body.get("message") or "").lower()
