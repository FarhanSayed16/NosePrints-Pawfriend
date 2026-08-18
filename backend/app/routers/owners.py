"""
Owner API routes — CRUD for dog owners.
PII list/get/update/delete require staff JWT.
Public create still requires explicit consent (prefer POST /register).
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db import get_db
from app.deps import get_current_staff
from app.models.database import Dog, Owner, StaffUser
from app.schemas import OwnerCreate, OwnerResponse, OwnerUpdate
from app.services import storage_service

router = APIRouter(prefix="/owners", tags=["Owners"])


@router.post("/", response_model=OwnerResponse, status_code=status.HTTP_201_CREATED)
async def create_owner(data: OwnerCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new dog owner. Explicit consent is required.
    Prefer POST /api/v1/register so owner + dog are created together.
    """
    owner = Owner(
        name=data.name,
        phone=data.phone,
        email=data.email,
        address=data.address,
        consent_given_at=datetime.now(timezone.utc),
        consent_text_version=settings.CONSENT_TEXT_VERSION,
    )
    db.add(owner)
    await db.flush()
    return owner


@router.get("/", response_model=list[OwnerResponse])
async def list_owners(
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
    _: StaffUser = Depends(get_current_staff),
):
    """List all owners with pagination. Staff only — contains phone/email."""
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Owner).offset(offset).limit(per_page).order_by(Owner.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{owner_id}", response_model=OwnerResponse)
async def get_owner(
    owner_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: StaffUser = Depends(get_current_staff),
):
    """Get a single owner by ID. Staff only."""
    result = await db.execute(select(Owner).where(Owner.id == owner_id))
    owner = result.scalar_one_or_none()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    return owner


@router.patch("/{owner_id}", response_model=OwnerResponse)
async def update_owner(
    owner_id: UUID,
    data: OwnerUpdate,
    db: AsyncSession = Depends(get_db),
    _: StaffUser = Depends(get_current_staff),
):
    """Update owner information. Staff only."""
    result = await db.execute(select(Owner).where(Owner.id == owner_id))
    owner = result.scalar_one_or_none()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(owner, field, value)

    await db.flush()
    return owner


@router.delete("/{owner_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_owner(
    owner_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: StaffUser = Depends(get_current_staff),
):
    """
    Delete owner and all associated data.
    DPDP Act compliance: supports full data erasure on request.
    Cascade deletes dogs and their nose prints, and removes stored photos.
    """
    result = await db.execute(
        select(Owner)
        .where(Owner.id == owner_id)
        .options(selectinload(Owner.dogs).selectinload(Dog.nose_prints))
    )
    owner = result.scalar_one_or_none()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    urls: list[str] = []
    for dog in owner.dogs:
        if dog.profile_photo_url:
            urls.append(dog.profile_photo_url)
        for print_row in dog.nose_prints:
            if print_row.image_url:
                urls.append(print_row.image_url)

    await db.delete(owner)
    for url in urls:
        await storage_service.delete_image(url)
