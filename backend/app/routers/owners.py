"""
Owner API routes — CRUD for dog owners.
Includes DPDP Act compliant data deletion.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.database import Owner
from app.schemas import OwnerCreate, OwnerResponse, OwnerUpdate

router = APIRouter(prefix="/owners", tags=["Owners"])


@router.post("/", response_model=OwnerResponse, status_code=status.HTTP_201_CREATED)
async def create_owner(data: OwnerCreate, db: AsyncSession = Depends(get_db)):
    """Register a new dog owner with DPDP Act consent timestamp."""
    owner = Owner(
        name=data.name,
        phone=data.phone,
        email=data.email,
        address=data.address,
        consent_given_at=datetime.now(timezone.utc),  # Consent recorded at creation
    )
    db.add(owner)
    await db.flush()
    return owner


@router.get("/", response_model=list[OwnerResponse])
async def list_owners(
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """List all owners with pagination."""
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Owner).offset(offset).limit(per_page).order_by(Owner.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{owner_id}", response_model=OwnerResponse)
async def get_owner(owner_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a single owner by ID."""
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
):
    """Update owner information."""
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
async def delete_owner(owner_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Delete owner and all associated data.
    DPDP Act compliance: supports full data erasure on request.
    Cascade deletes dogs and their nose prints.
    """
    result = await db.execute(select(Owner).where(Owner.id == owner_id))
    owner = result.scalar_one_or_none()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    await db.delete(owner)
