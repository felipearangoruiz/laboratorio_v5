"""add quick assessment tables

Revision ID: 20260416_0004
Revises: 20260411_0003
Create Date: 2026-04-16 00:00:01

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260416_0004"
down_revision = "20260411_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quick_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_name", sa.String(length=255), nullable=False),
        sa.Column("org_type", sa.String(length=50), nullable=False, server_default="empresa"),
        sa.Column("size_range", sa.String(length=20), nullable=False, server_default="1-10"),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("leader_responses", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("scores", postgresql.JSONB, nullable=True),
        sa.Column("member_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("responses_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quick_assessments")),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_quick_assessments_owner_id_users"),
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "quick_assessment_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("token", sa.String(length=32), nullable=False),
        sa.Column("responses", postgresql.JSONB, nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quick_assessment_members")),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["quick_assessments.id"],
            name=op.f("fk_quick_assessment_members_assessment_id_quick_assessments"),
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        op.f("ix_quick_assessment_members_token"),
        "quick_assessment_members",
        ["token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_quick_assessment_members_token"), table_name="quick_assessment_members")
    op.drop_table("quick_assessment_members")
    op.drop_table("quick_assessments")
