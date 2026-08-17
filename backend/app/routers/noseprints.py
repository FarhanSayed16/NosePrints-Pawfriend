"""
Nose Print API routes — upload, process, and manage biometric data.
Handles the full pipeline: upload → detect nose → quality check → extract embedding → store.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.database import Dog, NosePrint
from app.schemas import NosePrintResponse, QualityCheckResult
from app.services import (
    assess_image_quality,
    embedding_extractor,
    nose_detector,
    storage_service,
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/noseprints", tags=["Nose Prints"])


@router.post(
    "/upload/{dog_id}",
    response_model=NosePrintResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_nose_print(
    dog_id: UUID,
    file: UploadFile = File(..., description="Nose print photo (JPEG/PNG)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a nose print photo for a registered dog.

    Full pipeline:
    1. Validate the dog exists
    2. Check we haven't exceeded 5 embeddings per dog
    3. Read and validate the image
    4. Detect the nose region (YOLOv8)
    5. Quality check (sharpness, brightness, coverage)
    6. Extract embedding (ResNet50 → 512-d vector)
    7. Upload original photo to object storage
    8. Store embedding + metadata in database
    """
    # 1. Validate dog exists
    result = await db.execute(select(Dog).where(Dog.id == dog_id))
    dog = result.scalar_one_or_none()
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")

    # 2. Check embedding count (max 5 per dog for optimal matching)
    count_result = await db.execute(
        select(func.count(NosePrint.id)).where(NosePrint.dog_id == dog_id)
    )
    count = count_result.scalar() or 0
    if count >= 5:
        raise HTTPException(
            status_code=400,
            detail="Maximum of 5 nose prints per dog. Delete an existing one first.",
        )

    # 3. Read image
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    content_type = file.content_type or "image/jpeg"
    if content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WebP images are supported")

    # 4. Detect nose region
    nose_image, bbox = nose_detector.detect(image_bytes)

    # 5. Quality check
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
                "message": "Image quality check failed",
                "issues": quality.issues,
                "scores": {
                    "sharpness": quality.sharpness_score,
                    "brightness": quality.brightness_score,
                    "nose_coverage": quality.nose_coverage,
                },
            },
        )

    # 6. Extract embedding
    embedding = embedding_extractor.extract(nose_image)

    # 7. Upload to object storage
    image_url = await storage_service.upload_image(
        image_bytes,
        folder=f"nose-prints/{dog_id}",
        content_type=content_type,
    )

    # 8. Store in database
    is_primary = count == 0  # First nose print is primary
    nose_print = NosePrint(
        dog_id=dog_id,
        embedding=embedding.tolist(),
        image_url=image_url,
        quality_score=quality.sharpness_score,
        is_primary=is_primary,
    )
    db.add(nose_print)
    await db.flush()

    logger.info(f"Nose print uploaded for dog {dog_id}: quality={quality.sharpness_score:.1f}")

    return nose_print


@router.post("/quality-check", response_model=QualityCheckResult)
async def check_image_quality(
    file: UploadFile = File(..., description="Image to check quality"),
):
    """
    Pre-check image quality before full upload.
    Useful for the PWA to give real-time feedback during capture.
    """
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    # Detect nose for bbox
    _, bbox = nose_detector.detect(image_bytes)

    quality = assess_image_quality(image_bytes, nose_bbox=bbox)
    return quality


@router.get("/{dog_id}", response_model=list[NosePrintResponse])
async def get_nose_prints(dog_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get all nose prints for a dog."""
    result = await db.execute(
        select(NosePrint)
        .where(NosePrint.dog_id == dog_id)
        .order_by(NosePrint.is_primary.desc(), NosePrint.captured_at.desc())
    )
    return result.scalars().all()


@router.delete("/{noseprint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_nose_print(noseprint_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a specific nose print."""
    result = await db.execute(select(NosePrint).where(NosePrint.id == noseprint_id))
    nose_print = result.scalar_one_or_none()
    if not nose_print:
        raise HTTPException(status_code=404, detail="Nose print not found")

    # Delete photo from storage
    await storage_service.delete_image(nose_print.image_url)

    await db.delete(nose_print)
