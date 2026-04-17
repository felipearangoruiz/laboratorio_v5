"""add node_type to groups and org_structure_type to organizations

Revision ID: 20260417_0008
Revises: 20260417_0007
Create Date: 2026-04-17 18:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260417_0008"
down_revision = "20260417_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add node_type to groups ('person' or 'area')
    op.add_column(
        "groups",
        sa.Column("node_type", sa.String(20), nullable=False, server_default="area"),
    )
    # Add email to groups (for person nodes)
    op.add_column(
        "groups",
        sa.Column("email", sa.String(255), nullable=False, server_default=""),
    )
    # Add org_structure_type to organizations ('people', 'areas', 'mixed')
    op.add_column(
        "organizations",
        sa.Column("org_structure_type", sa.String(20), nullable=False, server_default="areas"),
    )


def downgrade() -> None:
    op.drop_column("organizations", "org_structure_type")
    op.drop_column("groups", "email")
    op.drop_column("groups", "node_type")
