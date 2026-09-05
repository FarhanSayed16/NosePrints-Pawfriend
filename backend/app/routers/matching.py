"""
Matching API routes — identify dogs by nose print scan.
The core identification flow: scan → match → human review.
"""

import cv2
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_staff
from app.models.database import StaffUser
from app.schemas import DetectPreviewResponse, MatchConfirmation, MatchConfirmResponse, MatchQueueItem, MatchResponse
from app.services import (
    confirm_match,
    embedding_extractor,
    find_matches,
    storage_service,
)
from app.services.capture_pipeline import prepare_nose_scan
from app.services.ml_guard import require_embedding_model
from app.services.nose_detector import nose_detector

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/match", tags=["Matching"])


@router.post("/detect-preview", response_model=DetectPreviewResponse)
async def detect_preview(
    file: UploadFile = File(..., description="Full dog, face, or close-up photo"),
):
    """
    Find a nose box so the user can confirm or adjust the crop.
    Does not run matching or the quality gate.
    """
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file")
    if not nose_detector.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nose detector is not loaded.",
        )
    try:
        detection = nose_detector.detect(image_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    h, w = detection.original.shape[:2]
    if detection.bbox is None:
        return DetectPreviewResponse(
            detected=False,
            confidence=0.0,
            image_width=w,
            image_height=h,
            bbox=None,
            message="No nose found — drag the box over the nose yourself.",
        )
    x1, y1, x2, y2 = detection.bbox
    return DetectPreviewResponse(
        detected=True,
        confidence=round(float(detection.confidence), 4),
        image_width=w,
        image_height=h,
        bbox={
            "x1": x1 / max(w, 1),
            "y1": y1 / max(h, 1),
            "x2": x2 / max(w, 1),
            "y2": y2 / max(h, 1),
        },
        message="Nose found — adjust the box if needed, then confirm.",
    )


@router.post("/identify", response_model=MatchResponse)
async def identify_dog(
    file: UploadFile = File(..., description="Nose crop or photo containing a nose"),
    appearance: UploadFile | None = File(default=None, description="Optional full dog / face photo"),
    pre_cropped: bool = Query(False),
    force_appearance: bool = Query(
        False,
        description="Override soft look-photo warning for the optional appearance file",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Identify a dog by scanning its nose print.

    Optional `appearance` is stored for staff side-by-side review and a coat-colour
    hint. It does not replace nose cosine as the identity signal.
    """
    from app.services.look_gate import assess_look_photo

    require_embedding_model()

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    scan = prepare_nose_scan(image_bytes, pre_cropped=pre_cropped)
    embedding = embedding_extractor.extract(scan.crop)
    quality = scan.quality

    ok, encoded = cv2.imencode(".jpg", scan.crop)
    crop_bytes = encoded.tobytes() if ok else image_bytes

    query_image_url = await storage_service.upload_image(
        crop_bytes,
        folder="match-queries",
        content_type="image/jpeg",
    )

    appearance_bytes = None
    if appearance is not None:
        appearance_bytes = await appearance.read()
        if not appearance_bytes:
            appearance_bytes = None
    query_appearance_url = None
    if appearance_bytes:
        # P1.1: same soft look gate as profile-photo
        gate = assess_look_photo(appearance_bytes)
        if not gate.ok:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": gate.issues[0] if gate.issues else "Look photo rejected",
                    "issues": gate.issues,
                    "soft_warn": False,
                    "scores": gate.scores,
                },
            )
        if gate.soft_warn and not force_appearance:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": gate.issues[0] if gate.issues else "Please confirm this is a dog photo",
                    "issues": gate.issues,
                    "soft_warn": True,
                    "scores": gate.scores,
                    "suggestions": [
                        "Choose a full-body or face photo of the dog",
                        "Or tap Use anyway, then search again",
                    ],
                },
            )
        query_appearance_url = await storage_service.upload_image(
            appearance_bytes,
            folder="match-appearance",
            content_type="image/jpeg",
        )

    match_result = await find_matches(
        db=db,
        query_embedding=embedding,
        quality_result=quality,
        query_image_url=query_image_url,
        query_appearance_url=query_appearance_url,
        query_appearance_bytes=appearance_bytes,
    )

    logger.info(
        f"Identify request: match_found={match_result.match_found}, "
        f"top_score={match_result.top_score}, "
        f"candidates={len(match_result.candidates)}, "
        f"appearance={'yes' if query_appearance_url else 'no'}"
    )

    return match_result


@router.get("/queue", response_model=list[MatchQueueItem])
async def match_queue(
    include_reviewed: bool = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: StaffUser = Depends(get_current_staff),
):
    """Staff match queue. Owner contact is not included until confirm."""
    from app.services.matcher import list_match_queue

    return await list_match_queue(
        db,
        include_reviewed=include_reviewed,
        page=page,
        per_page=per_page,
    )


@router.post("/confirm", response_model=MatchConfirmResponse)
async def confirm_match_result(
    data: MatchConfirmation,
    db: AsyncSession = Depends(get_db),
    staff: StaffUser = Depends(get_current_staff),
):
    """
    Staff confirms or rejects a match.
    Owner contact is returned only when confirmed=true.
    """
    try:
        result = await confirm_match(
            db=db,
            match_log_id=data.match_log_id,
            confirmed=data.confirmed,
            confirmed_by=staff.id,
            staff_notes=data.staff_notes,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
