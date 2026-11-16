"""Nationwide staff: invites, reset, audit, region columns.

Revision ID: 20261116_nationwide
Revises: 20260818_p3
Create Date: 2026-11-16
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20261116_nationwide"
down_revision: Union[str, Sequence[str], None] = "20260818_p3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE staff_users "
        "ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE"
    )
    op.execute("ALTER TABLE staff_users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ")
    op.execute("ALTER TABLE dogs ADD COLUMN IF NOT EXISTS region VARCHAR(100)")
    op.execute("ALTER TABLE dogs ADD COLUMN IF NOT EXISTS shelter_code VARCHAR(64)")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS staff_invites (
            id UUID PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL,
            token_hash VARCHAR(64) NOT NULL UNIQUE,
            invited_by UUID REFERENCES staff_users(id) ON DELETE SET NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            accepted_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id UUID PRIMARY KEY,
            staff_id UUID NOT NULL REFERENCES staff_users(id) ON DELETE CASCADE,
            token_hash VARCHAR(64) NOT NULL UNIQUE,
            expires_at TIMESTAMPTZ NOT NULL,
            used_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id UUID PRIMARY KEY,
            actor_staff_id UUID REFERENCES staff_users(id) ON DELETE SET NULL,
            action VARCHAR(64) NOT NULL,
            resource_type VARCHAR(64),
            resource_id VARCHAR(64),
            detail TEXT,
            ip_address VARCHAR(64),
            created_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_staff_invites_email ON staff_invites (email)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs (action)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs (created_at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_logs")
    op.execute("DROP TABLE IF EXISTS password_reset_tokens")
    op.execute("DROP TABLE IF EXISTS staff_invites")
    op.execute("ALTER TABLE dogs DROP COLUMN IF EXISTS shelter_code")
    op.execute("ALTER TABLE dogs DROP COLUMN IF EXISTS region")
    op.execute("ALTER TABLE staff_users DROP COLUMN IF EXISTS updated_at")
    op.execute("ALTER TABLE staff_users DROP COLUMN IF EXISTS is_active")
