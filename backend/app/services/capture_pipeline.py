"""
Shared capture pipeline: detect nose → reject misses → quality + heuristics on crop.

Client crop (`pre_cropped`) is a hint only — we never accept a frame when the
detector finds no nose. G1 re-detects on the crop and applies junk heuristics
before any embedding is stored or searched.
"""

from dataclasses import dataclass

import numpy as np
from fastapi import HTTPException, status

from app.config import settings
from app.schemas import QualityCheckResult
from app.services.nose_detector import DetectionResult, nose_detector
from app.services.nose_heuristics import assess_nose_crop_heuristics, encode_bgr_jpeg
from app.services.quality import assess_crop_quality


NO_NOSE_DETAIL = {
    "message": "No dog nose detected in this photo",
    "issues": ["The camera did not find a nose region"],
    "suggestions": [
        "Hold the phone 15–30 cm from the nose",
        "Align the nose inside the on-screen circle",
        "Use even lighting and avoid motion blur",
        "Keep a little muzzle around the nose — do not crop so tight the nose fills the whole photo",
        "Do not upload keyboards, rooms, or other non-nose photos",
    ],
}

LOW_CONF_DETAIL = {
    "message": "Nose detection is too uncertain for a reliable print",
    "issues": ["Detector confidence below the acceptance threshold"],
    "suggestions": [
        "Get a closer, sharper photo of the black nose leather",
        "Fill most of the crop box with the nose, not the whole face or body",
        "Avoid busy backgrounds and non-dog objects",
    ],
}

HEURISTIC_DETAIL = {
    "message": "This photo does not look like a usable dog nose print",
    "suggestions": [
        "Crop tightly on the black/pink nose leather",
        "Do not use keyboards, screens, rooms, or whole-body shots as the nose print",
        "Retake outdoors or under even light, 15–30 cm from the nose",
    ],
}


@dataclass
class PreparedScan:
    original: np.ndarray
    crop: np.ndarray
    bbox: tuple[int, int, int, int]
    confidence: float
    quality: QualityCheckResult


def _require_detection(
    detection: DetectionResult,
    *,
    reject_full_frame: bool = False,
) -> None:
    """
    Require a usable YOLO hit.

    reject_full_frame: only for the first pass on a full scene photo.
    Do NOT use on client crops / re-detect — a tight nose crop often fills most of the canvas.
    """
    if detection.bbox is None or detection.crop is None or detection.crop.size == 0:
        raise HTTPException(status_code=422, detail=NO_NOSE_DETAIL)

    min_conf = settings.DETECTOR_MIN_ACCEPT_CONF
    if float(detection.confidence) < min_conf:
        detail = {
            **LOW_CONF_DETAIL,
            "issues": [
                *LOW_CONF_DETAIL["issues"],
                f"Confidence {float(detection.confidence):.2f} < minimum {min_conf:.2f}",
            ],
            "scores": {"detector_confidence": round(float(detection.confidence), 4)},
        }
        raise HTTPException(status_code=422, detail=detail)

    if reject_full_frame:
        x1, y1, x2, y2 = detection.bbox
        oh, ow = detection.original.shape[:2]
        frac = (max(0, x2 - x1) * max(0, y2 - y1)) / max(1, ow * oh)
        if frac > settings.NOSE_MAX_BBOX_FRAME_FRACTION:
            raise HTTPException(
                status_code=422,
                detail={
                    **HEURISTIC_DETAIL,
                    "message": "No clear nose crop — detection covered almost the whole photo",
                    "issues": [
                        "Detected region covers almost the whole photo — tighten the box on the nose leather only.",
                        "Do not upload keyboards, laptop screens, or room photos as nose prints.",
                    ],
                    "scores": {
                        "detector_confidence": round(float(detection.confidence), 4),
                        "bbox_frame_fraction": round(frac, 4),
                    },
                },
            )


def _redetect_on_crop(crop_bgr: np.ndarray) -> DetectionResult:
    """G1.1 — run YOLO again on the cropped JPEG bytes."""
    crop_bytes = encode_bgr_jpeg(crop_bgr)
    return nose_detector.detect(crop_bytes)


def prepare_nose_scan(image_bytes: bytes, *, pre_cropped: bool = False) -> PreparedScan:
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    # P2.1: client crops skip frame coverage — require re-detect so junk cannot skip YOLO
    if pre_cropped and not settings.NOSE_REDETECT_ON_CROP:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Client crops require nose re-detection to be enabled",
                "issues": ["NOSE_REDETECT_ON_CROP is disabled while pre_cropped=true"],
                "suggestions": [
                    "Enable NOSE_REDETECT_ON_CROP on the server",
                    "Or upload a full frame without a client crop",
                ],
            },
        )

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

    # Client already framed the nose: if YOLO misses on a tight leather crop,
    # soft-accept only when heuristics clearly look like nose leather (not fur/fabric).
    if (
        pre_cropped
        and (detection.bbox is None or detection.crop is None or detection.crop.size == 0)
    ):
        full = detection.original
        fh, fw = full.shape[:2]
        provisional = assess_nose_crop_heuristics(full, pre_cropped=True)
        likeness = float(provisional.scores.get("nose_likeness", 0.0))
        if (
            provisional.passed
            and min(fh, fw) >= 64
            and likeness >= settings.NOSE_SOFT_MISS_MIN_LIKENESS
        ):
            detection = DetectionResult(
                original=full,
                crop=full.copy(),
                bbox=(0, 0, fw, fh),
                confidence=max(float(detection.confidence), settings.DETECTOR_MIN_ACCEPT_CONF),
            )
        else:
            raise HTTPException(status_code=422, detail=NO_NOSE_DETAIL)

    # Full-frame reject only on uncropped scene photos — never on client crops
    _require_detection(detection, reject_full_frame=not pre_cropped)

    orig_h, orig_w = detection.original.shape[:2]
    crop = detection.crop
    bbox = detection.bbox
    confidence = float(detection.confidence)

    # G1.1: after a full-frame detect, re-run YOLO on the crop itself.
    # Client-confirmed crops are already crop-sized; still re-detect when enabled
    # so a junk crop cannot skip a second opinion.
    if settings.NOSE_REDETECT_ON_CROP:
        try:
            second = _redetect_on_crop(crop)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        second_ok = (
            second.bbox is not None
            and second.crop is not None
            and second.crop.size > 0
            and float(second.confidence) >= settings.DETECTOR_MIN_ACCEPT_CONF
        )

        if second_ok:
            # Prefer the tighter crop from the second pass when it exists
            crop = second.crop
            confidence = min(confidence, float(second.confidence))
            if pre_cropped:
                ch, cw = second.original.shape[:2]
                bbox = second.bbox
                orig_h, orig_w = ch, cw
        elif pre_cropped and settings.NOSE_REDETECT_SOFT_FALLBACK:
            # Tight real-nose crops often confuse a second YOLO pass — keep first
            # only when likeness is clearly nose-like (blocks fur/blanket soft-pass).
            fallback = assess_nose_crop_heuristics(
                crop, bbox=bbox, frame_w=orig_w, frame_h=orig_h, pre_cropped=True
            )
            likeness = float(fallback.scores.get("nose_likeness", 0.0))
            if (
                not fallback.passed
                or likeness < settings.NOSE_REDETECT_SOFT_MIN_LIKENESS
            ):
                raise HTTPException(status_code=422, detail=NO_NOSE_DETAIL)
            # keep first-pass crop / bbox / confidence
        else:
            _require_detection(second, reject_full_frame=False)

    quality = assess_crop_quality(
        crop,
        bbox,
        orig_w,
        orig_h,
        check_coverage=not pre_cropped,
    )
    if not quality.passed:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Image quality too low for a reliable nose print",
                "issues": quality.issues,
                "suggestions": [
                    "Get closer so the black nose leather fills most of the crop box",
                    "Hold the phone steady — a zoomed-in body photo will look blurry",
                    "Use even lighting and avoid shadows on the nose",
                ],
                "scores": {
                    "sharpness": quality.sharpness_score,
                    "brightness": quality.brightness_score,
                    "nose_coverage": quality.nose_coverage,
                    "detector_confidence": confidence,
                },
            },
        )

    # G1.2 / G1.4 — aspect, edges, grid, nose-likeness
    gate = assess_nose_crop_heuristics(
        crop,
        bbox=bbox,
        frame_w=orig_w,
        frame_h=orig_h,
        pre_cropped=pre_cropped,
    )
    if not gate.passed:
        raise HTTPException(
            status_code=422,
            detail={
                **HEURISTIC_DETAIL,
                "issues": gate.issues,
                "scores": {**gate.scores, "detector_confidence": round(confidence, 4)},
            },
        )

    return PreparedScan(
        original=detection.original,
        crop=crop,
        bbox=bbox,
        confidence=confidence,
        quality=quality,
    )
