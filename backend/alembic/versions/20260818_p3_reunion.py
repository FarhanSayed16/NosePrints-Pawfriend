"""Phase 3 reunion columns (additive).

Revision ID: 20260818_p3
Revises:
Create Date: 2026-08-18

Does not replace create_all for local DEBUG. Use this on shared databases:
    cd backend && alembic upgrade head
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260818_p3"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE dogs ADD COLUMN IF NOT EXISTS last_seen_note TEXT")
    op.execute("ALTER TABLE dogs ADD COLUMN IF NOT EXISTS found_notes TEXT")
    op.execute(
        "ALTER TABLE dogs ADD COLUMN IF NOT EXISTS listed_as_found_at TIMESTAMPTZ"
    )
    op.execute("ALTER TABLE match_logs ADD COLUMN IF NOT EXISTS staff_notes TEXT")
    op.execute(
        "ALTER TABLE owners ADD COLUMN IF NOT EXISTS consent_text_version "
        "VARCHAR(32) NOT NULL DEFAULT 'v1'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE dogs DROP COLUMN IF EXISTS last_seen_note")
    op.execute("ALTER TABLE dogs DROP COLUMN IF EXISTS found_notes")
    op.execute("ALTER TABLE dogs DROP COLUMN IF EXISTS listed_as_found_at")
    op.execute("ALTER TABLE match_logs DROP COLUMN IF EXISTS staff_notes")
