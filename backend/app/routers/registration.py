"""
Combined public registration — owner + dog in one transaction.
Prevents orphan owner rows if dog creation fails.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models.database import Dog, Owner
from app.routers.dogs import _dog_to_response
from app.schemas import CombinedRegisterRequest, CombinedRegisterResponse

router = APIRouter(tags=["Registration"])


@router.post(
    "/register",
    response_model=CombinedRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_owner_and_dog(
    data: CombinedRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Public registration: explicit consent required.
    Creates owner and dog together so a failed second step cannot leave an orphan owner.
    """
    if data.owner.consent is not True:
        raise HTTPException(
            status_code=400,
            detail="Explicit consent is required to register under India's DPDP Act 2023.",
        )

    owner = Owner(
        name=data.owner.name,
        phone=data.owner.phone,
        email=data.owner.email,
        address=data.owner.address,
        consent_given_at=datetime.now(timezone.utc),
        consent_text_version=settings.CONSENT_TEXT_VERSION,
    )
    db.add(owner)
    await db.flush()

    dog = Dog(
        owner_id=owner.id,
        name=data.dog.name,
        breed=data.dog.breed,
        color=data.dog.color,
        sex=data.dog.sex,
        approx_dob=data.dog.approx_dob,
        microchip_id=data.dog.microchip_id,
        status=data.dog.status or "registered",
    )
    db.add(dog)
    await db.flush()

    return CombinedRegisterResponse(
        owner=owner,
        dog=_dog_to_response(dog, 0),
        message="Owner and dog registered. Next: upload 3–5 nose prints.",
    )
