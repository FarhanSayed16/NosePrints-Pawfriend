"""
Nose Print API routes — upload, process, and manage biometric data.
Handles the full pipeline: upload → detect nose → quality check → extract embedding → store.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.database import Dog, NosePrint
from app.schemas import NosePrintResponse, QualityCheckResult
from app.services import (
    embedding_extractor,
    nose_detector,
    storage_service,
)
from app.services.capture_pipeline import prepare_nose_scan
from app.services.ml_guard import require_embedding_model
from app.services.quality import assess_crop_quality

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/noseprints", tags=["Nose Prints"])

_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def sniff_image_content_type(data: bytes, declared: str | None) -> str:
    """Accept empty/Android MIME types when the bytes are clearly an image."""
    raw = (declared or "").lower().split(";")[0].strip()
    if raw in {"image/jpg", "image/pjpeg"}:
        raw = "image/jpeg"
    if raw in _IMAGE_TYPES:
        return raw
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG"):
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    raise HTTPException(
        status_code=400,
        detail="Only JPEG, PNG, and WebP images are supported. HEIC must be converted on the phone.",
    )


@router.post(
    "/upload/{dog_id}",
    response_model=NosePrintResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_nose_print(
    dog_id: UUID,
    file: UploadFile = File(..., description="Nose print photo (JPEG/PNG)"),
    pre_cropped: bool = Query(False),
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
    require_embedding_model()

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

    content_type = sniff_image_content_type(image_bytes, file.content_type)

    # 4–5. Detect nose (reject misses) + quality on crop
    scan = prepare_nose_scan(image_bytes, pre_cropped=pre_cropped)

    # 6. Extract embedding from the cropped nose
    embedding = embedding_extractor.extract(scan.crop)
    quality = scan.quality

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

    if not nose_detector.is_loaded:
        raise HTTPException(
            status_code=503,
            detail="Nose detector is not loaded. Train and place nose_detector.onnx.",
        )

    detection = nose_detector.detect(image_bytes)
    if detection.bbox is None or detection.crop is None:
        return QualityCheckResult(
            passed=False,
            sharpness_score=0.0,
            brightness_score=0.0,
            nose_coverage=0.0,
            issues=["No dog nose detected — move closer and align the nose in the circle"],
        )

    orig_h, orig_w = detection.original.shape[:2]
    return assess_crop_quality(detection.crop, detection.bbox, orig_w, orig_h)


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
