"""
Owner API routes — CRUD for dog owners.
PII list/get/update/delete require staff JWT.
Public create still requires explicit consent (prefer POST /register).
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db import get_db
from app.deps import get_current_staff, require_admin
from app.models.database import Dog, Owner, StaffUser
from app.services.audit import record_audit
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
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: StaffUser = Depends(get_current_staff),
):
    """List all owners with pagination. Staff only — contains phone/email."""
    offset = (page - 1) * per_page
    query = select(Owner)
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.where(
            or_(Owner.name.ilike(term), Owner.email.ilike(term), Owner.phone.ilike(term))
        )
    result = await db.execute(
        query.offset(offset).limit(min(per_page, 100)).order_by(Owner.created_at.desc())
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
    staff: StaffUser = Depends(require_admin),
):
    """
    Delete owner and all associated data.
    DPDP Act compliance: supports full data erasure on request.
    Cascade deletes dogs and their nose prints, and removes stored photos.
    Admin only — audited.
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

    await record_audit(
        db,
        action="owner.erase",
        actor_staff_id=staff.id,
        resource_type="owner",
        resource_id=owner_id,
        detail={"email": owner.email, "dogs": len(owner.dogs)},
    )
    await db.delete(owner)
    for url in urls:
        await storage_service.delete_image(url)
