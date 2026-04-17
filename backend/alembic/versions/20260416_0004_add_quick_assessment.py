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


# Declare the enum type separately with create_type=False so it's never
# auto-created when used inside column definitions. We create/drop it
# explicitly with checkfirst=True so the migration is idempotent and
# never crashes with "type already exists".
quick_assessment_status = postgresql.ENUM(
    "waiting",
    "ready",
    "completed",
    name="quick_assessment_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    # Create the enum type explicitly — checkfirst ensures we don't crash
    # if it already exists in the database.
    quick_assessment_status.create(bind, checkfirst=True)

    op.create_table(
        "quick_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("leader_responses", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("scores", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("member_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status",
            quick_assessment_status,
            nullable=False,
            server_default="waiting",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_quick_assessments"),
    )

    op.create_table(
        "quick_assessment_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("quick_assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role_label", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("token", sa.String(length=32), nullable=False),
        sa.Column("responses", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_quick_assessment_members"),
    )

    op.create_index(
        "ix_quick_assessment_members_token",
        "quick_assessment_members",
        ["token"],
        unique=True,
    )
    op.create_index(
        "ix_quick_assessment_members_assessment_id",
        "quick_assessment_members",
        ["assessment_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_quick_assessment_members_assessment_id")
    op.drop_index("ix_quick_assessment_members_token")
    op.drop_table("quick_assessment_members")
    op.drop_table("quick_assessments")

    # Drop the enum type explicitly — checkfirst avoids crash if already gone.
    quick_assessment_status.drop(op.get_bind(), checkfirst=True)
