"""add context_notes to groups

Revision ID: 20260417_0002
Revises: 20260417_0001
Create Date: 2026-04-17 21:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260417_0002"
down_revision = "20260417_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "groups",
        sa.Column("context_notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("groups", "context_notes")
