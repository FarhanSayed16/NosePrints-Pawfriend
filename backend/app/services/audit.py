"""Structured audit logging for staff ops actions."""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AuditLog

logger = logging.getLogger(__name__)


async def record_audit(
    db: AsyncSession,
    *,
    action: str,
    actor_staff_id: UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | UUID | None = None,
    detail: dict[str, Any] | str | None = None,
    ip_address: str | None = None,
) -> None:
    """Persist an audit row. Never raises to callers — logs on failure."""
    try:
        detail_text: str | None
        if detail is None:
            detail_text = None
        elif isinstance(detail, str):
            detail_text = detail
        else:
            detail_text = json.dumps(detail, default=str)

        db.add(
            AuditLog(
                actor_staff_id=actor_staff_id,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id is not None else None,
                detail=detail_text,
                ip_address=ip_address,
            )
        )
        await db.flush()
    except Exception as exc:
        logger.warning("audit log failed (%s): %s", action, exc)
