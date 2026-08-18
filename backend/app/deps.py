"""
FastAPI dependencies — staff JWT auth for protected routes.
"""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models.database import StaffUser

bearer_scheme = HTTPBearer(auto_error=True)
optional_bearer = HTTPBearer(auto_error=False)


async def get_current_staff(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> StaffUser:
    """Require a valid staff JWT. Used on owner PII and match confirmation."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Staff login required",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        staff_id = payload.get("sub")
        if not staff_id:
            raise credentials_exc
        staff_uuid = UUID(staff_id)
    except (JWTError, ValueError):
        raise credentials_exc

    result = await db.execute(select(StaffUser).where(StaffUser.id == staff_uuid))
    staff = result.scalar_one_or_none()
    if staff is None:
        raise credentials_exc
    return staff


async def get_optional_staff(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    db: AsyncSession = Depends(get_db),
) -> StaffUser | None:
    """Return staff if a valid JWT is present; otherwise None (public caller)."""
    if credentials is None:
        return None
    try:
        return await get_current_staff(credentials, db)
    except HTTPException:
        return None
