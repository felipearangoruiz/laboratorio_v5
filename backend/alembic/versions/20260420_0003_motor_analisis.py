"""motor de análisis — 7 tablas nuevas para el pipeline de 4 pasos

Tablas creadas (en orden de FK):
  analysis_runs → node_analyses, group_analyses, org_analyses,
  document_extractions, findings → recommendations → evidence_links

Revision ID: 20260420_0005
Revises: 20260420_0004
Create Date: 2026-04-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260420_0005"
down_revision = "20260420_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. analysis_runs ─────────────────────────────────────────────
    op.create_table(
        "analysis_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.VARCHAR(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "started_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("model_used", sa.VARCHAR(100), nullable=True),
        sa.Column(
            "total_nodes",
            sa.INTEGER,
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "total_groups",
            sa.INTEGER,
            nullable=False,
            server_default="0",
        ),
        sa.Column("error_message", sa.TEXT, nullable=True),
    )
    op.create_index("ix_analysis_runs_org_id", "analysis_runs", ["org_id"])
    op.create_index("ix_analysis_runs_status", "analysis_runs", ["status"])

    # ── 2. node_analyses ─────────────────────────────────────────────
    op.create_table(
        "node_analyses",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "signals_positive",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "signals_tension",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "themes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "dimensions_touched",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("evidence_type", sa.VARCHAR(20), nullable=True),
        sa.Column("emotional_intensity", sa.VARCHAR(10), nullable=True),
        sa.Column(
            "key_quotes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "context_notes_used",
            sa.BOOLEAN,
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "confidence",
            sa.FLOAT,
            nullable=False,
            server_default="0.5",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_node_analyses_run_id", "node_analyses", ["run_id"])
    op.create_index("ix_node_analyses_group_id", "node_analyses", ["group_id"])

    # ── 3. group_analyses ────────────────────────────────────────────
    op.create_table(
        "group_analyses",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "patterns_internal",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "dominant_themes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("tension_level", sa.VARCHAR(10), nullable=True),
        sa.Column(
            "scores_by_dimension",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("gap_leader_team", sa.FLOAT, nullable=True),
        sa.Column(
            "coverage",
            sa.FLOAT,
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "confidence",
            sa.FLOAT,
            nullable=False,
            server_default="0.5",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_group_analyses_run_id", "group_analyses", ["run_id"])
    op.create_index("ix_group_analyses_group_id", "group_analyses", ["group_id"])

    # ── 4. org_analyses ──────────────────────────────────────────────
    op.create_table(
        "org_analyses",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "cross_patterns",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "contradictions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "structural_risks",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "dimension_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "network_metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "confidence",
            sa.FLOAT,
            nullable=False,
            server_default="0.5",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_org_analyses_run_id", "org_analyses", ["run_id"])
    op.create_index("ix_org_analyses_org_id", "org_analyses", ["org_id"])

    # ── 5. document_extractions ──────────────────────────────────────
    op.create_table(
        "document_extractions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "doc_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("doc_type", sa.VARCHAR(20), nullable=False),
        sa.Column(
            "extracted_structure",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "key_indicators",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "implicit_signals",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "injected_at_step",
            sa.INTEGER,
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_document_extractions_run_id", "document_extractions", ["run_id"]
    )
    op.create_index(
        "ix_document_extractions_doc_id", "document_extractions", ["doc_id"]
    )

    # ── 6. findings ──────────────────────────────────────────────────
    op.create_table(
        "findings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.VARCHAR(500), nullable=False),
        sa.Column("description", sa.TEXT, nullable=False),
        sa.Column("type", sa.VARCHAR(20), nullable=False),
        sa.Column("severity", sa.VARCHAR(10), nullable=False, server_default="media"),
        sa.Column(
            "dimensions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "node_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "confidence",
            sa.FLOAT,
            nullable=False,
            server_default="0.5",
        ),
        sa.Column("confidence_rationale", sa.TEXT, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_findings_run_id", "findings", ["run_id"])
    op.create_index("ix_findings_org_id", "findings", ["org_id"])

    # ── 7. recommendations ───────────────────────────────────────────
    op.create_table(
        "recommendations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "finding_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("findings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.VARCHAR(500), nullable=False),
        sa.Column("description", sa.TEXT, nullable=False),
        sa.Column(
            "priority",
            sa.INTEGER,
            nullable=False,
            server_default="99",
        ),
        sa.Column("impact", sa.VARCHAR(10), nullable=False, server_default="medio"),
        sa.Column("effort", sa.VARCHAR(10), nullable=False, server_default="medio"),
        sa.Column(
            "horizon",
            sa.VARCHAR(15),
            nullable=False,
            server_default="corto",
        ),
        sa.Column(
            "node_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_recommendations_run_id", "recommendations", ["run_id"])
    op.create_index(
        "ix_recommendations_finding_id", "recommendations", ["finding_id"]
    )

    # ── 8. evidence_links ────────────────────────────────────────────
    op.create_table(
        "evidence_links",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "finding_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("findings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "node_analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("node_analyses.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "group_analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("group_analyses.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("quote", sa.TEXT, nullable=True),
        sa.Column("evidence_type", sa.VARCHAR(20), nullable=False),
    )
    op.create_index(
        "ix_evidence_links_finding_id", "evidence_links", ["finding_id"]
    )


def downgrade() -> None:
    # Drop in reverse FK order
    op.drop_index("ix_evidence_links_finding_id", table_name="evidence_links")
    op.drop_table("evidence_links")

    op.drop_index("ix_recommendations_finding_id", table_name="recommendations")
    op.drop_index("ix_recommendations_run_id", table_name="recommendations")
    op.drop_table("recommendations")

    op.drop_index("ix_findings_org_id", table_name="findings")
    op.drop_index("ix_findings_run_id", table_name="findings")
    op.drop_table("findings")

    op.drop_index(
        "ix_document_extractions_doc_id", table_name="document_extractions"
    )
    op.drop_index(
        "ix_document_extractions_run_id", table_name="document_extractions"
    )
    op.drop_table("document_extractions")

    op.drop_index("ix_org_analyses_org_id", table_name="org_analyses")
    op.drop_index("ix_org_analyses_run_id", table_name="org_analyses")
    op.drop_table("org_analyses")

    op.drop_index("ix_group_analyses_group_id", table_name="group_analyses")
    op.drop_index("ix_group_analyses_run_id", table_name="group_analyses")
    op.drop_table("group_analyses")

    op.drop_index("ix_node_analyses_group_id", table_name="node_analyses")
    op.drop_index("ix_node_analyses_run_id", table_name="node_analyses")
    op.drop_table("node_analyses")

    op.drop_index("ix_analysis_runs_status", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_org_id", table_name="analysis_runs")
    op.drop_table("analysis_runs")
