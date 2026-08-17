"""
Matching API routes — identify dogs by nose print scan.
The core identification flow: scan → match → human review.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas import MatchConfirmation, MatchResponse
from app.services import (
    assess_image_quality,
    confirm_match,
    embedding_extractor,
    find_matches,
    nose_detector,
    storage_service,
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/match", tags=["Matching"])


@router.post("/identify", response_model=MatchResponse)
async def identify_dog(
    file: UploadFile = File(..., description="Nose print photo to match against database"),
    db: AsyncSession = Depends(get_db),
):
    """
    Identify a dog by scanning its nose print.

    This is the primary identification endpoint — used when someone
    finds a stray dog and wants to check if it's registered.

    Pipeline:
    1. Read and validate image
    2. Detect nose region
    3. Quality check
    4. Extract embedding
    5. Upload query image to storage (for audit trail)
    6. Run pgvector similarity search
    7. Return candidates (human confirmation required before contact reveal)
    """
    # 1. Read image
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    content_type = file.content_type or "image/jpeg"

    # 2. Detect nose
    nose_image, bbox = nose_detector.detect(image_bytes)

    # 3. Quality check
    quality = assess_image_quality(
        image_bytes,
        nose_bbox=bbox,
        frame_width=nose_image.shape[1] if bbox else None,
        frame_height=nose_image.shape[0] if bbox else None,
    )

    if not quality.passed:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Image quality too low for reliable matching",
                "issues": quality.issues,
                "suggestions": [
                    "Hold the phone steady and close to the dog's nose",
                    "Ensure good lighting — avoid shadows on the nose",
                    "The nose should fill most of the camera frame",
                ],
            },
        )

    # 4. Extract embedding
    embedding = embedding_extractor.extract(nose_image)

    # 5. Store query image (audit trail)
    query_image_url = await storage_service.upload_image(
        image_bytes,
        folder="match-queries",
        content_type=content_type,
    )

    # 6. Similarity search
    match_result = await find_matches(
        db=db,
        query_embedding=embedding,
        quality_result=quality,
        query_image_url=query_image_url,
    )

    logger.info(
        f"Identify request: match_found={match_result.match_found}, "
        f"top_score={match_result.top_score}, "
        f"candidates={len(match_result.candidates)}"
    )

    return match_result


@router.post("/confirm")
async def confirm_match_result(
    data: MatchConfirmation,
    db: AsyncSession = Depends(get_db),
):
    """
    Staff confirms or rejects a match.
    REQUIRED before any owner contact information is released.

    This is the human-in-the-loop safety step — never auto-resolve matches.
    """
    try:
        result = await confirm_match(
            db=db,
            match_log_id=data.match_log_id,
            confirmed=data.confirmed,
            confirmed_by=data.confirmed_by,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
