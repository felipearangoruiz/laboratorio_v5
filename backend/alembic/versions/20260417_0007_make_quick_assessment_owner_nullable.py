"""make quick_assessment owner_id nullable for anonymous free flow

Revision ID: 20260417_0007
Revises: 20260417_0006
Create Date: 2026-04-17 12:00:00

"""

from alembic import op
import sqlalchemy as sa

revision = "20260417_0007"
down_revision = "20260417_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "quick_assessments",
        "owner_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    # Update FK to SET NULL on delete instead of CASCADE
    op.drop_constraint(
        "fk_quick_assessments_owner_id_users",
        "quick_assessments",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_quick_assessments_owner_id_users",
        "quick_assessments",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_quick_assessments_owner_id_users",
        "quick_assessments",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_quick_assessments_owner_id_users",
        "quick_assessments",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column(
        "quick_assessments",
        "owner_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=False,
    )
