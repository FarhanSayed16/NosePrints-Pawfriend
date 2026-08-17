"""
Matching API routes — identify dogs by nose print scan.
The core identification flow: scan → match → human review.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_staff
from app.models.database import StaffUser
from app.schemas import MatchConfirmation, MatchResponse
from app.services import (
    confirm_match,
    embedding_extractor,
    find_matches,
    storage_service,
)
from app.services.capture_pipeline import prepare_nose_scan
from app.services.ml_guard import require_embedding_model

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
    require_embedding_model()

    # 1. Read image
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    content_type = file.content_type or "image/jpeg"

    scan = prepare_nose_scan(image_bytes)
    embedding = embedding_extractor.extract(scan.crop)
    quality = scan.quality

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
    staff: StaffUser = Depends(get_current_staff),
):
    """
    Staff confirms or rejects a match.
    REQUIRED before any owner contact information is released.
    """
    try:
        result = await confirm_match(
            db=db,
            match_log_id=data.match_log_id,
            confirmed=data.confirmed,
            confirmed_by=staff.id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
