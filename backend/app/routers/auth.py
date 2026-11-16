"""
Staff auth — bootstrap, login, invite, password reset, staff admin.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.deps import get_current_staff, require_admin
from app.models.database import (
    AuditLog,
    PasswordResetToken,
    StaffInvite,
    StaffUser,
)
from app.schemas import (
    AuditLogItem,
    StaffAcceptInviteRequest,
    StaffInviteCreate,
    StaffInviteResponse,
    StaffListItem,
    StaffLoginRequest,
    StaffMeResponse,
    StaffPasswordResetConfirm,
    StaffPasswordResetRequest,
    StaffPasswordResetResponse,
    StaffRoleUpdate,
    StaffTokenResponse,
)
from app.services.audit import record_audit
from app.services.auth import create_access_token, hash_password, verify_password
from app.services.notify import (
    notify_staff_invite,
    notify_staff_password_reset,
    smtp_configured,
)
from app.services.tokens import generate_raw_token, hash_token

router = APIRouter(prefix="/auth", tags=["Auth"])


def _app_base_url(request: Request | None = None) -> str:
    if settings.PUBLIC_APP_URL:
        return settings.PUBLIC_APP_URL.rstrip("/")
    if request is not None:
        # Prefer Origin / Referer for SPA behind tunnel
        origin = request.headers.get("origin")
        if origin:
            return origin.rstrip("/")
    return "http://localhost:5173"


def _client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/bootstrap", response_model=StaffTokenResponse)
async def bootstrap_first_staff(
    data: StaffLoginRequest,
    request: Request,
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
        is_active=True,
    )
    db.add(staff)
    await db.flush()
    await record_audit(
        db,
        action="staff.bootstrap",
        actor_staff_id=staff.id,
        resource_type="staff",
        resource_id=staff.id,
        ip_address=_client_ip(request),
    )

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
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Staff login — returns a JWT for owner PII and match confirmation."""
    result = await db.execute(
        select(StaffUser).where(StaffUser.email == data.email.lower().strip())
    )
    staff = result.scalar_one_or_none()
    if staff is None or not verify_password(data.password, staff.password_hash):
        await record_audit(
            db,
            action="staff.login_failed",
            detail={"email": data.email.lower().strip()},
            ip_address=_client_ip(request),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not getattr(staff, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff account is deactivated",
        )

    await record_audit(
        db,
        action="staff.login",
        actor_staff_id=staff.id,
        resource_type="staff",
        resource_id=staff.id,
        ip_address=_client_ip(request),
    )

    token = create_access_token(staff_id=staff.id, email=staff.email, role=staff.role)
    return StaffTokenResponse(
        access_token=token,
        staff_id=staff.id,
        email=staff.email,
        role=staff.role,
    )


@router.get("/me", response_model=StaffMeResponse)
async def staff_me(staff: StaffUser = Depends(get_current_staff)):
    """Current staff user from JWT."""
    return StaffMeResponse(
        staff_id=staff.id,
        email=staff.email,
        role=staff.role,
        is_active=getattr(staff, "is_active", True),
    )


@router.post("/invite", response_model=StaffInviteResponse)
async def create_invite(
    data: StaffInviteCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: StaffUser = Depends(require_admin),
):
    """Admin invites a new staff member (or re-invites pending)."""
    email = data.email.lower().strip()
    existing = await db.execute(select(StaffUser).where(StaffUser.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Staff with this email already exists")

    raw = generate_raw_token()
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.STAFF_INVITE_EXPIRY_HOURS)
    invite = StaffInvite(
        email=email,
        role=data.role,
        token_hash=hash_token(raw),
        invited_by=admin.id,
        expires_at=expires,
    )
    db.add(invite)
    await db.flush()

    accept_url = f"{_app_base_url(request)}/staff/accept-invite?token={raw}"
    email_sent = notify_staff_invite(email, accept_url, data.role)
    await record_audit(
        db,
        action="staff.invite",
        actor_staff_id=admin.id,
        resource_type="staff_invite",
        resource_id=invite.id,
        detail={"email": email, "role": data.role, "email_sent": email_sent},
        ip_address=_client_ip(request),
    )

    return StaffInviteResponse(
        id=invite.id,
        email=invite.email,
        role=invite.role,
        expires_at=invite.expires_at,
        accepted_at=invite.accepted_at,
        email_sent=email_sent,
        accept_url=None if email_sent and smtp_configured() else accept_url,
    )


@router.get("/invites", response_model=list[StaffInviteResponse])
async def list_invites(
    db: AsyncSession = Depends(get_db),
    _: StaffUser = Depends(require_admin),
):
    """List pending (unaccepted) invites."""
    rows = (
        await db.execute(
            select(StaffInvite)
            .where(StaffInvite.accepted_at.is_(None))
            .order_by(StaffInvite.created_at.desc())
            .limit(100)
        )
    ).scalars().all()
    return [
        StaffInviteResponse(
            id=row.id,
            email=row.email,
            role=row.role,
            expires_at=row.expires_at,
            accepted_at=row.accepted_at,
            email_sent=False,
            accept_url=None,
        )
        for row in rows
    ]


@router.post("/accept-invite", response_model=StaffTokenResponse)
async def accept_invite(
    data: StaffAcceptInviteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Accept invite token and set password — creates staff user."""
    token_h = hash_token(data.token)
    invite = (
        await db.execute(select(StaffInvite).where(StaffInvite.token_hash == token_h))
    ).scalar_one_or_none()
    if invite is None or invite.accepted_at is not None:
        raise HTTPException(status_code=400, detail="Invalid or already used invite")
    if invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invite has expired")

    existing = await db.execute(select(StaffUser).where(StaffUser.email == invite.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Staff already exists for this email")

    staff = StaffUser(
        email=invite.email,
        password_hash=hash_password(data.password),
        role=invite.role,
        is_active=True,
    )
    db.add(staff)
    invite.accepted_at = datetime.now(timezone.utc)
    await db.flush()
    await record_audit(
        db,
        action="staff.accept_invite",
        actor_staff_id=staff.id,
        resource_type="staff",
        resource_id=staff.id,
        ip_address=_client_ip(request),
    )

    token = create_access_token(staff_id=staff.id, email=staff.email, role=staff.role)
    return StaffTokenResponse(
        access_token=token,
        staff_id=staff.id,
        email=staff.email,
        role=staff.role,
    )


@router.post("/request-password-reset", response_model=StaffPasswordResetResponse)
async def request_password_reset(
    data: StaffPasswordResetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Request password reset. Always returns a generic message to avoid email enumeration.
    When SMTP is unset and the email exists, includes reset_url for staging copy.
    """
    generic = StaffPasswordResetResponse(
        message="If that email is registered, a reset link was issued.",
        email_sent=False,
        reset_url=None,
    )
    email = data.email.lower().strip()
    staff = (
        await db.execute(select(StaffUser).where(StaffUser.email == email))
    ).scalar_one_or_none()
    if staff is None or not getattr(staff, "is_active", True):
        return generic

    raw = generate_raw_token()
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.STAFF_RESET_EXPIRY_HOURS)
    db.add(
        PasswordResetToken(
            staff_id=staff.id,
            token_hash=hash_token(raw),
            expires_at=expires,
        )
    )
    await db.flush()
    reset_url = f"{_app_base_url(request)}/staff/reset-password?token={raw}"
    email_sent = notify_staff_password_reset(email, reset_url)
    await record_audit(
        db,
        action="staff.password_reset_request",
        actor_staff_id=staff.id,
        resource_type="staff",
        resource_id=staff.id,
        detail={"email_sent": email_sent},
        ip_address=_client_ip(request),
    )

    return StaffPasswordResetResponse(
        message=generic.message,
        email_sent=email_sent,
        reset_url=None if email_sent and smtp_configured() else reset_url,
    )


@router.post("/reset-password", response_model=StaffTokenResponse)
async def reset_password(
    data: StaffPasswordResetConfirm,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Complete password reset with one-time token."""
    token_h = hash_token(data.token)
    row = (
        await db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_h)
        )
    ).scalar_one_or_none()
    if row is None or row.used_at is not None:
        raise HTTPException(status_code=400, detail="Invalid or already used reset token")
    if row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset token has expired")

    staff = (
        await db.execute(select(StaffUser).where(StaffUser.id == row.staff_id))
    ).scalar_one_or_none()
    if staff is None or not getattr(staff, "is_active", True):
        raise HTTPException(status_code=400, detail="Staff account unavailable")

    staff.password_hash = hash_password(data.password)
    row.used_at = datetime.now(timezone.utc)
    await db.flush()
    await record_audit(
        db,
        action="staff.password_reset",
        actor_staff_id=staff.id,
        resource_type="staff",
        resource_id=staff.id,
        ip_address=_client_ip(request),
    )

    token = create_access_token(staff_id=staff.id, email=staff.email, role=staff.role)
    return StaffTokenResponse(
        access_token=token,
        staff_id=staff.id,
        email=staff.email,
        role=staff.role,
    )


@router.get("/staff", response_model=list[StaffListItem])
async def list_staff(
    db: AsyncSession = Depends(get_db),
    _: StaffUser = Depends(require_admin),
):
    rows = (
        await db.execute(select(StaffUser).order_by(StaffUser.created_at.asc()))
    ).scalars().all()
    return [
        StaffListItem(
            staff_id=s.id,
            email=s.email,
            role=s.role,
            is_active=getattr(s, "is_active", True),
            created_at=s.created_at,
        )
        for s in rows
    ]


@router.patch("/staff/{staff_id}/role", response_model=StaffListItem)
async def update_staff_role(
    staff_id: UUID,
    data: StaffRoleUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: StaffUser = Depends(require_admin),
):
    if staff_id == admin.id and data.role != "admin":
        raise HTTPException(status_code=400, detail="Cannot demote your own admin role")
    staff = (
        await db.execute(select(StaffUser).where(StaffUser.id == staff_id))
    ).scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    staff.role = data.role
    await db.flush()
    await record_audit(
        db,
        action="staff.role_update",
        actor_staff_id=admin.id,
        resource_type="staff",
        resource_id=staff_id,
        detail={"role": data.role},
        ip_address=_client_ip(request),
    )
    return StaffListItem(
        staff_id=staff.id,
        email=staff.email,
        role=staff.role,
        is_active=getattr(staff, "is_active", True),
        created_at=staff.created_at,
    )


@router.post("/staff/{staff_id}/deactivate", response_model=StaffListItem)
async def deactivate_staff(
    staff_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: StaffUser = Depends(require_admin),
):
    if staff_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    staff = (
        await db.execute(select(StaffUser).where(StaffUser.id == staff_id))
    ).scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    staff.is_active = False
    await db.flush()
    await record_audit(
        db,
        action="staff.deactivate",
        actor_staff_id=admin.id,
        resource_type="staff",
        resource_id=staff_id,
        ip_address=_client_ip(request),
    )
    return StaffListItem(
        staff_id=staff.id,
        email=staff.email,
        role=staff.role,
        is_active=False,
        created_at=staff.created_at,
    )


@router.get("/audit", response_model=list[AuditLogItem])
async def list_audit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: StaffUser = Depends(require_admin),
):
    offset = (page - 1) * per_page
    rows = (
        await db.execute(
            select(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
    ).scalars().all()
    return rows
