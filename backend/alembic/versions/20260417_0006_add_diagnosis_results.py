"""add diagnosis_results table

Revision ID: 20260417_0006
Revises: 20260416_0005
Create Date: 2026-04-17 00:00:01

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260417_0006"
down_revision = "20260416_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "diagnosis_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("scores", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("narrative", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("network_metrics", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_diagnosis_results")),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_diagnosis_results_organization_id_organizations"),
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    op.drop_table("diagnosis_results")
