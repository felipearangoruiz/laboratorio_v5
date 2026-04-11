"""add strategic context to organizations

Revision ID: 20260411_0003
Revises: 20260407_0002
Create Date: 2026-04-11 00:00:03

"""

from alembic import op
import sqlalchemy as sa


revision = "20260411_0003"
down_revision = "20260407_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("strategic_objectives", sa.String(), nullable=False, server_default=""),
    )
    op.add_column(
        "organizations",
        sa.Column("strategic_concerns", sa.String(), nullable=False, server_default=""),
    )
    op.add_column(
        "organizations",
        sa.Column("key_questions", sa.String(), nullable=False, server_default=""),
    )
    op.add_column(
        "organizations",
        sa.Column("additional_context", sa.String(), nullable=False, server_default=""),
    )

    op.alter_column("organizations", "strategic_objectives", server_default=None)
    op.alter_column("organizations", "strategic_concerns", server_default=None)
    op.alter_column("organizations", "key_questions", server_default=None)
    op.alter_column("organizations", "additional_context", server_default=None)


def downgrade() -> None:
    op.drop_column("organizations", "additional_context")
    op.drop_column("organizations", "key_questions")
    op.drop_column("organizations", "strategic_concerns")
    op.drop_column("organizations", "strategic_objectives")
