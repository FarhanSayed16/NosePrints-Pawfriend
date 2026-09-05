"""
Dog API routes — CRUD for dog profiles + search/filter.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.deps import get_current_staff, get_optional_staff
from app.models.database import Dog, NosePrint, StaffUser
from app.config import settings
from app.schemas import (
    DogCreate,
    DogResponse,
    DogUpdate,
    FoundIntakeRequest,
    LookCheckResult,
    ReportLostRequest,
)
from app.services import embedding_extractor, storage_service

router = APIRouter(prefix="/dogs", tags=["Dogs"])


def _dog_to_response(dog: Dog, nose_print_count: int = 0, *, staff_view: bool = False) -> DogResponse:
    """Convert ORM Dog to response schema with nose print count."""
    return DogResponse(
        id=dog.id,
        owner_id=dog.owner_id,
        name=dog.name,
        breed=dog.breed,
        color=dog.color,
        sex=dog.sex,
        approx_dob=dog.approx_dob.date() if dog.approx_dob else None,
        microchip_id=dog.microchip_id,
        status=dog.status,
        last_seen_latitude=dog.last_seen_latitude,
        last_seen_longitude=dog.last_seen_longitude,
        last_seen_at=dog.last_seen_at,
        last_seen_note=dog.last_seen_note,
        found_notes=dog.found_notes if staff_view else None,
        listed_as_found_at=dog.listed_as_found_at,
        profile_photo_url=dog.profile_photo_url,
        nose_print_count=nose_print_count,
        created_at=dog.created_at,
    )


@router.post("/", response_model=DogResponse, status_code=status.HTTP_201_CREATED)
async def create_dog(data: DogCreate, db: AsyncSession = Depends(get_db)):
    """Register a new dog profile."""
    dog = Dog(
        owner_id=data.owner_id,
        name=data.name,
        breed=data.breed,
        color=data.color,
        sex=data.sex,
        approx_dob=data.approx_dob,
        microchip_id=data.microchip_id,
        status=data.status,
    )
    db.add(dog)
    await db.flush()
    return _dog_to_response(dog, 0)


@router.get("/", response_model=list[DogResponse])
async def list_dogs(
    breed: str | None = Query(None, description="Filter by breed"),
    color: str | None = Query(None, description="Filter by color"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status: registered/lost/found"),
    name: str | None = Query(None, description="Search by name (partial match)"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    List/search dogs with filters.
    This is the searchable directory from Phase 1.
    """
    query = select(Dog)

    # Apply filters
    if breed:
        query = query.where(Dog.breed.ilike(f"%{breed}%"))
    if color:
        query = query.where(Dog.color.ilike(f"%{color}%"))
    if status_filter:
        query = query.where(Dog.status == status_filter)
    if name:
        query = query.where(Dog.name.ilike(f"%{name}%"))

    # Pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(Dog.created_at.desc())

    result = await db.execute(query)
    dogs = result.scalars().all()

    # Get nose print counts efficiently
    responses = []
    for dog in dogs:
        count_result = await db.execute(
            select(func.count(NosePrint.id)).where(NosePrint.dog_id == dog.id)
        )
        count = count_result.scalar() or 0
        responses.append(_dog_to_response(dog, count))

    return responses


@router.get("/lost", response_model=list[DogResponse])
async def list_lost_dogs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all dogs currently marked as lost."""
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Dog)
        .where(Dog.status == "lost")
        .offset(offset)
        .limit(per_page)
        .order_by(Dog.last_seen_at.desc().nulls_last())
    )
    dogs = result.scalars().all()
    return [_dog_to_response(dog) for dog in dogs]


@router.get("/found", response_model=list[DogResponse])
async def list_found_dogs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all dogs currently marked as found (unmatched strays)."""
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Dog)
        .where(Dog.status == "found")
        .offset(offset)
        .limit(per_page)
        .order_by(Dog.created_at.desc())
    )
    dogs = result.scalars().all()
    return [_dog_to_response(dog) for dog in dogs]


@router.post("/found-intake", response_model=DogResponse, status_code=status.HTTP_201_CREATED)
async def found_dog_intake(
    data: FoundIntakeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    List a scanned stray as found without owner registration.
    Used after identify returns no match.
    Finder phone is stored for staff only (not returned on this public response).
    """
    now = datetime.now(timezone.utc)
    note_parts = []
    if data.finder_nickname:
        note_parts.append(f"Finder: {data.finder_nickname}")
    if data.finder_phone:
        note_parts.append(f"Finder phone: {data.finder_phone}")
    if data.location_note:
        note_parts.append(f"Location: {data.location_note}")
    if data.notes:
        note_parts.append(data.notes)

    photo_url = None
    if data.query_image_url:
        if not storage_service.is_trusted_url(data.query_image_url):
            raise HTTPException(
                status_code=400,
                detail="query_image_url must be a photo stored by this app",
            )
        photo_url = data.query_image_url

    dog = Dog(
        owner_id=None,
        name=None,
        breed=data.breed,
        color=data.color,
        status="found",
        last_seen_latitude=data.last_seen_latitude,
        last_seen_longitude=data.last_seen_longitude,
        last_seen_at=now,
        last_seen_note=data.location_note,
        found_notes="\n".join(note_parts) or None,
        listed_as_found_at=now,
        profile_photo_url=photo_url,
    )
    db.add(dog)
    await db.flush()

    print_count = 0
    if photo_url:
        image_bytes = await storage_service.read_image(photo_url)
        if image_bytes:
            from app.services.capture_pipeline import prepare_nose_scan
            from app.services.ml_guard import require_embedding_model
            import cv2

            require_embedding_model()
            try:
                # P0.1: never embed raw bytes — same nose gate as register/identify
                scan = prepare_nose_scan(image_bytes, pre_cropped=True)
            except HTTPException:
                # Keep the found listing (look/context) but do not pollute the gallery
                logger = __import__("logging").getLogger(__name__)
                logger.warning("found-intake: query image failed nose gate — listing without nose print")
            else:
                embedding = embedding_extractor.extract(scan.crop)
                ok, encoded = cv2.imencode(".jpg", scan.crop)
                crop_bytes = encoded.tobytes() if ok else image_bytes
                gated_url = await storage_service.upload_image(
                    crop_bytes,
                    folder="nose-prints/found",
                    content_type="image/jpeg",
                )
                db.add(
                    NosePrint(
                        dog_id=dog.id,
                        embedding=embedding.tolist(),
                        image_url=gated_url,
                        is_primary=True,
                    )
                )
                print_count = 1

    return _dog_to_response(dog, print_count)


@router.get("/{dog_id}", response_model=DogResponse)
async def get_dog(
    dog_id: UUID,
    db: AsyncSession = Depends(get_db),
    staff: StaffUser | None = Depends(get_optional_staff),
):
    """Get a single dog profile by ID. Finder notes only if staff JWT is present."""
    result = await db.execute(select(Dog).where(Dog.id == dog_id))
    dog = result.scalar_one_or_none()
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")

    count_result = await db.execute(
        select(func.count(NosePrint.id)).where(NosePrint.dog_id == dog_id)
    )
    count = count_result.scalar() or 0
    return _dog_to_response(dog, count, staff_view=staff is not None)


@router.post("/look-check", response_model=LookCheckResult)
async def look_photo_check(
    file: UploadFile = File(..., description="Full body or face photo to soft-check"),
):
    """
    G3.1 — Soft gate for look photos (not biometric).
    Does not store anything. Frontend may warn and allow “Use anyway”.
    """
    from app.services.look_gate import assess_look_photo

    image_bytes = await file.read()
    result = assess_look_photo(image_bytes)
    if not result.ok:
        return LookCheckResult(
            ok=False,
            soft_warn=False,
            issues=result.issues,
            scores=result.scores,
            message=result.issues[0] if result.issues else "Photo rejected",
        )
    if result.soft_warn:
        return LookCheckResult(
            ok=True,
            soft_warn=True,
            issues=result.issues,
            scores=result.scores,
            message=result.issues[0] if result.issues else "Please confirm this is a dog photo",
        )
    return LookCheckResult(ok=True, soft_warn=False, issues=[], scores=result.scores, message="Looks usable")


@router.post("/{dog_id}/profile-photo", response_model=DogResponse)
async def upload_profile_photo(
    dog_id: UUID,
    file: UploadFile = File(..., description="Full body or face photo of the dog"),
    force: bool = Query(False, description="Override soft look-photo warning"),
    db: AsyncSession = Depends(get_db),
    staff: StaffUser | None = Depends(get_optional_staff),
):
    """Store a coat/body reference photo. Not a nose print.

    P2.6: public overwrite only within PROFILE_PHOTO_OPEN_HOURS of dog creation,
    unless staff JWT is present. Rate-limited via middleware.
    """
    from datetime import timedelta

    from app.services.look_gate import assess_look_photo

    result = await db.execute(select(Dog).where(Dog.id == dog_id))
    dog = result.scalar_one_or_none()
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")

    if staff is None:
        created = dog.created_at
        if created is not None:
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            open_hours = settings.PROFILE_PHOTO_OPEN_HOURS
            if datetime.now(timezone.utc) - created > timedelta(hours=open_hours):
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Profile photo window expired. Ask PawFriend staff to update the look photo, "
                        f"or upload within {open_hours} hours of registration."
                    ),
                )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    gate = assess_look_photo(image_bytes)
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
    if gate.soft_warn and not force:
        raise HTTPException(
            status_code=422,
            detail={
                "message": gate.issues[0] if gate.issues else "Please confirm this is a dog photo",
                "issues": gate.issues,
                "soft_warn": True,
                "scores": gate.scores,
                "suggestions": [
                    "Choose a full-body or face photo of the dog",
                    "Or tap Use anyway if you are sure (staff will see this photo)",
                ],
            },
        )

    previous = dog.profile_photo_url
    url = await storage_service.upload_image(
        image_bytes,
        folder="dog-profiles",
        content_type=file.content_type or "image/jpeg",
    )
    dog.profile_photo_url = url
    await db.flush()
    if previous and previous != url:
        await storage_service.delete_image(previous)

    count_result = await db.execute(
        select(func.count(NosePrint.id)).where(NosePrint.dog_id == dog_id)
    )
    count = count_result.scalar() or 0
    return _dog_to_response(dog, count)


@router.patch("/{dog_id}", response_model=DogResponse)
async def update_dog(
    dog_id: UUID,
    data: DogUpdate,
    db: AsyncSession = Depends(get_db),
    _: StaffUser = Depends(get_current_staff),
):
    """Update a dog profile. Staff only — includes mark lost/found."""
    result = await db.execute(select(Dog).where(Dog.id == dog_id))
    dog = result.scalar_one_or_none()
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dog, field, value)

    await db.flush()

    count_result = await db.execute(
        select(func.count(NosePrint.id)).where(NosePrint.dog_id == dog_id)
    )
    count = count_result.scalar() or 0
    return _dog_to_response(dog, count, staff_view=True)


@router.post("/{dog_id}/report-lost", response_model=DogResponse)
async def report_dog_lost(
    dog_id: UUID,
    data: ReportLostRequest,
    db: AsyncSession = Depends(get_db),
    _: StaffUser = Depends(get_current_staff),
):
    """Mark a registered dog as lost. Staff only (owners contact PawFriend)."""
    result = await db.execute(select(Dog).where(Dog.id == dog_id))
    dog = result.scalar_one_or_none()
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")

    dog.status = "lost"
    dog.last_seen_at = datetime.now(timezone.utc)
    if data.last_seen_latitude is not None:
        dog.last_seen_latitude = data.last_seen_latitude
    if data.last_seen_longitude is not None:
        dog.last_seen_longitude = data.last_seen_longitude
    if data.last_seen_note is not None:
        dog.last_seen_note = data.last_seen_note

    await db.flush()
    count_result = await db.execute(
        select(func.count(NosePrint.id)).where(NosePrint.dog_id == dog_id)
    )
    count = count_result.scalar() or 0
    return _dog_to_response(dog, count, staff_view=True)


@router.delete("/{dog_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dog(
    dog_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: StaffUser = Depends(get_current_staff),
):
    """Delete a dog, associated nose prints, match logs, and stored photos. Staff only."""
    from app.models.database import MatchLog

    result = await db.execute(
        select(Dog)
        .where(Dog.id == dog_id)
        .options(selectinload(Dog.nose_prints))
    )
    dog = result.scalar_one_or_none()
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")

    urls = [p.image_url for p in dog.nose_prints if p.image_url]
    if dog.profile_photo_url:
        urls.append(dog.profile_photo_url)

    # P3.8: purge match logs that pointed at this dog (and their query photos)
    log_result = await db.execute(
        select(MatchLog).where(MatchLog.top_match_dog_id == dog_id)
    )
    for log in log_result.scalars().all():
        if log.query_image_url:
            urls.append(log.query_image_url)
        if getattr(log, "query_appearance_url", None):
            urls.append(log.query_appearance_url)
        await db.delete(log)

    await db.delete(dog)
    # Deduplicate URLs; best-effort storage cleanup after DB delete
    for url in dict.fromkeys(urls):
        await storage_service.delete_image(url)
