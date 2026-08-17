"""
Dog API routes — CRUD for dog profiles + search/filter.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db import get_db
from app.models.database import Dog, NosePrint
from app.schemas import DogCreate, DogResponse, DogUpdate

router = APIRouter(prefix="/dogs", tags=["Dogs"])


def _dog_to_response(dog: Dog, nose_print_count: int = 0) -> DogResponse:
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


@router.get("/{dog_id}", response_model=DogResponse)
async def get_dog(dog_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a single dog profile by ID."""
    result = await db.execute(select(Dog).where(Dog.id == dog_id))
    dog = result.scalar_one_or_none()
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")

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
):
    """Update a dog profile. Use this to mark a dog as lost/found."""
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
    return _dog_to_response(dog, count)


@router.delete("/{dog_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dog(dog_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a dog and all associated nose prints (cascade)."""
    result = await db.execute(select(Dog).where(Dog.id == dog_id))
    dog = result.scalar_one_or_none()
    if not dog:
        raise HTTPException(status_code=404, detail="Dog not found")
    await db.delete(dog)
