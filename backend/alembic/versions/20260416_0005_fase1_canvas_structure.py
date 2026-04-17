"""Fase 1: canvas structure — add positions to groups, lateral relations, memberships

Revision ID: 20260416_0005
Revises: 20260416_0004
Create Date: 2026-04-16 12:00:00

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260416_0005"
down_revision = "20260416_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add canvas fields to groups
    op.add_column("groups", sa.Column("area", sa.String(255), nullable=False, server_default=""))
    op.add_column("groups", sa.Column("position_x", sa.Float(), nullable=False, server_default="0"))
    op.add_column("groups", sa.Column("position_y", sa.Float(), nullable=False, server_default="0"))

    # Create lateral_relations table
    op.create_table(
        "lateral_relations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(50), nullable=False, server_default="colaboracion"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lateral_relations")),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name=op.f("fk_lateral_relations_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_node_id"], ["groups.id"],
            name=op.f("fk_lateral_relations_source_node_id_groups"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_node_id"], ["groups.id"],
            name=op.f("fk_lateral_relations_target_node_id_groups"),
            ondelete="CASCADE",
        ),
    )

    # Create memberships table
    op.create_table(
        "memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="admin"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_memberships")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name=op.f("fk_memberships_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.id"],
            name=op.f("fk_memberships_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("user_id", "org_id", name="uq_memberships_user_org"),
    )


def downgrade() -> None:
    op.drop_table("memberships")
    op.drop_table("lateral_relations")
    op.drop_column("groups", "position_y")
    op.drop_column("groups", "position_x")
    op.drop_column("groups", "area")
