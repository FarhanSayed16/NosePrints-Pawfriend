"""
Shared capture pipeline: detect nose → reject misses → quality on crop.
"""

from dataclasses import dataclass

import numpy as np
from fastapi import HTTPException, status

from app.schemas import QualityCheckResult
from app.services.nose_detector import DetectionResult, nose_detector
from app.services.quality import assess_crop_quality


NO_NOSE_DETAIL = {
    "message": "No dog nose detected in this photo",
    "issues": ["The camera did not find a nose region"],
    "suggestions": [
        "Hold the phone 15–30 cm from the nose",
        "Align the nose inside the on-screen circle",
        "Use even lighting and avoid motion blur",
        "Keep a little muzzle around the nose — do not crop so tight the nose fills the whole photo",
    ],
}


@dataclass
class PreparedScan:
    original: np.ndarray
    crop: np.ndarray
    bbox: tuple[int, int, int, int]
    confidence: float
    quality: QualityCheckResult


def prepare_nose_scan(image_bytes: bytes) -> PreparedScan:
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    if not nose_detector.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Nose detector is not loaded. Train YOLOv8-nano "
                "(ml/training/train_detector.py) and place backend/models/nose_detector.onnx."
            ),
        )

    try:
        detection: DetectionResult = nose_detector.detect(image_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if detection.bbox is None or detection.crop is None or detection.crop.size == 0:
        raise HTTPException(status_code=422, detail=NO_NOSE_DETAIL)

    orig_h, orig_w = detection.original.shape[:2]
    quality = assess_crop_quality(
        detection.crop,
        detection.bbox,
        orig_w,
        orig_h,
    )
    if not quality.passed:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Image quality too low for a reliable nose print",
                "issues": quality.issues,
                "suggestions": [
                    "Hold the phone steady and close to the dog's nose",
                    "Ensure good lighting — avoid shadows on the nose",
                    "Keep the nose inside the guide circle with a little muzzle visible",
                ],
                "scores": {
                    "sharpness": quality.sharpness_score,
                    "brightness": quality.brightness_score,
                    "nose_coverage": quality.nose_coverage,
                    "detector_confidence": detection.confidence,
                },
            },
        )

    return PreparedScan(
        original=detection.original,
        crop=detection.crop,
        bbox=detection.bbox,
        confidence=detection.confidence,
        quality=quality,
    )
