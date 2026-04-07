"""add parent_group_id

Revision ID: 20260407_0002
Revises: 20260406_0001
Create Date: 2026-04-07 00:00:02

"""

from alembic import op
import sqlalchemy as sa


revision = "20260407_0002"
down_revision = "20260406_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "groups",
        sa.Column("parent_group_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_groups_parent_group_id",
        "groups",
        "groups",
        ["parent_group_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_groups_parent_group_id",
        "groups",
        type_="foreignkey",
    )
    op.drop_column("groups", "parent_group_id")
