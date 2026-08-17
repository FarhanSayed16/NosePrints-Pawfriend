"""
Staff authentication helpers — password hashing and JWT issue/verify.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

WEAK_JWT_SECRETS = {
    "CHANGE_ME_IN_PRODUCTION",
    "change-me-in-production-use-a-real-secret",
    "dev-only-not-for-production-change-me-32b",
    "",
}


def jwt_secret_is_unsafe(secret: str) -> bool:
    return secret in WEAK_JWT_SECRETS or len(secret) < 32


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(*, staff_id: UUID, email: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
    payload = {
        "sub": str(staff_id),
        "email": email,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
