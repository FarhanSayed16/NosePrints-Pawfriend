"""
Staff auth routes — bootstrap first admin, then login for JWT.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.database import StaffUser
from app.schemas import StaffLoginRequest, StaffTokenResponse
from app.services.auth import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/bootstrap", response_model=StaffTokenResponse)
async def bootstrap_first_staff(
    data: StaffLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create the first staff admin. Disabled once any staff user exists.
    Use this once on a fresh database, then log in via /auth/login.
    """
    count = await db.scalar(select(func.count()).select_from(StaffUser))
    if count and count > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff already exists. Use /auth/login.",
        )

    staff = StaffUser(
        email=data.email.lower().strip(),
        password_hash=hash_password(data.password),
        role="admin",
    )
    db.add(staff)
    await db.flush()

    token = create_access_token(staff_id=staff.id, email=staff.email, role=staff.role)
    return StaffTokenResponse(
        access_token=token,
        staff_id=staff.id,
        email=staff.email,
        role=staff.role,
    )


@router.post("/login", response_model=StaffTokenResponse)
async def login(
    data: StaffLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Staff login — returns a JWT for owner PII and match confirmation."""
    result = await db.execute(
        select(StaffUser).where(StaffUser.email == data.email.lower().strip())
    )
    staff = result.scalar_one_or_none()
    if staff is None or not verify_password(data.password, staff.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(staff_id=staff.id, email=staff.email, role=staff.role)
    return StaffTokenResponse(
        access_token=token,
        staff_id=staff.id,
        email=staff.email,
        role=staff.role,
    )
