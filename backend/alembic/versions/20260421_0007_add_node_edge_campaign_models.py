"""add_node_edge_campaign_models

Revision ID: 20260421_0007
Revises: 20260420_0006
Create Date: 2026-04-21

Sprint 1 Prompt 1.1 — materializa el modelo Node+Edge documentado en
docs/MODEL_PHILOSOPHY.md. Crea 4 tablas nuevas y agrega campaign_id a
documents. NO toca ninguna tabla del motor de analisis existente.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "20260421_0007"
down_revision = "20260420_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Crear tipos ENUM (native PostgreSQL enums)
    # ------------------------------------------------------------------
    node_type_enum = postgresql.ENUM(
        "unit", "person", name="node_type_enum", create_type=False
    )
    edge_type_enum = postgresql.ENUM(
        "lateral", "process", name="edge_type_enum", create_type=False
    )
    campaign_status_enum = postgresql.ENUM(
        "draft", "active", "closed", name="campaign_status_enum", create_type=False
    )
    node_state_status_enum = postgresql.ENUM(
        "invited", "in_progress", "completed", "skipped",
        name="node_state_status_enum", create_type=False,
    )

    op.execute("CREATE TYPE node_type_enum AS ENUM ('unit', 'person')")
    op.execute("CREATE TYPE edge_type_enum AS ENUM ('lateral', 'process')")
    op.execute("CREATE TYPE campaign_status_enum AS ENUM ('draft', 'active', 'closed')")
    op.execute(
        "CREATE TYPE node_state_status_enum AS ENUM "
        "('invited', 'in_progress', 'completed', 'skipped')"
    )

    # ------------------------------------------------------------------
    # 2. Tabla assessment_campaigns
    # ------------------------------------------------------------------
    op.create_table(
        "assessment_campaigns",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "status",
            campaign_status_enum,
            nullable=False,
            server_default="draft",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_assessment_campaigns_organization_id",
        "assessment_campaigns",
        ["organization_id"],
    )

    # ------------------------------------------------------------------
    # 3. Tabla nodes
    # ------------------------------------------------------------------
    op.create_table(
        "nodes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("nodes.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "type",
            node_type_enum,
            nullable=False,
            server_default="unit",
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("position_x", sa.Float(), nullable=False, server_default="0"),
        sa.Column("position_y", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "attrs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_nodes_organization_id", "nodes", ["organization_id"])

    # ------------------------------------------------------------------
    # 4. Tabla edges
    # ------------------------------------------------------------------
    op.create_table(
        "edges",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("nodes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "target_node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("nodes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "edge_type",
            edge_type_enum,
            nullable=False,
            server_default="lateral",
        ),
        sa.Column(
            "edge_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_edges_organization_id", "edges", ["organization_id"])

    # ------------------------------------------------------------------
    # 5. Tabla node_states
    # ------------------------------------------------------------------
    op.create_table(
        "node_states",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "campaign_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assessment_campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email_assigned", sa.String(255), nullable=True),
        sa.Column("role_label", sa.String(255), nullable=True),
        sa.Column("context_notes", sa.Text(), nullable=True),
        sa.Column("respondent_token", sa.String(64), nullable=True),
        sa.Column(
            "status",
            node_state_status_enum,
            nullable=False,
            server_default="invited",
        ),
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("node_id", "campaign_id", name="uq_node_state_node_campaign"),
    )
    op.create_index("ix_node_states_node_id", "node_states", ["node_id"])
    op.create_index("ix_node_states_campaign_id", "node_states", ["campaign_id"])
    op.create_index(
        "ix_node_states_respondent_token",
        "node_states",
        ["respondent_token"],
        unique=True,
    )

    # ------------------------------------------------------------------
    # 6. Agregar campaign_id a documents
    # ------------------------------------------------------------------
    op.add_column(
        "documents",
        sa.Column(
            "campaign_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assessment_campaigns.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_documents_campaign_id", "documents", ["campaign_id"])


def downgrade() -> None:
    # Revertir en orden inverso a dependencias

    # 6. Quitar campaign_id de documents
    op.drop_index("ix_documents_campaign_id", table_name="documents")
    op.drop_column("documents", "campaign_id")

    # 5. Quitar node_states
    op.drop_index("ix_node_states_respondent_token", table_name="node_states")
    op.drop_index("ix_node_states_campaign_id", table_name="node_states")
    op.drop_index("ix_node_states_node_id", table_name="node_states")
    op.drop_table("node_states")

    # 4. Quitar edges
    op.drop_index("ix_edges_organization_id", table_name="edges")
    op.drop_table("edges")

    # 3. Quitar nodes
    op.drop_index("ix_nodes_organization_id", table_name="nodes")
    op.drop_table("nodes")

    # 2. Quitar assessment_campaigns
    op.drop_index("ix_assessment_campaigns_organization_id", table_name="assessment_campaigns")
    op.drop_table("assessment_campaigns")

    # 1. Quitar tipos ENUM
    op.execute("DROP TYPE node_state_status_enum")
    op.execute("DROP TYPE campaign_status_enum")
    op.execute("DROP TYPE edge_type_enum")
    op.execute("DROP TYPE node_type_enum")
