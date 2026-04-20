"""update diagnosis_results — new schema for external Codex processor

Changes:
  - Drop columns: narrative, network_metrics
  - Add columns: findings, recommendations, narrative_md, structure_snapshot, completed_at
  - Rename server_default of status from 'running' to 'processing'
  - Data migration: 'running' → 'processing', 'completed' → 'ready'

Revision ID: 20260420_0004
Revises: 20260418_0003
Create Date: 2026-04-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260420_0004"
down_revision = "20260418_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Drop legacy columns ──
    op.drop_column("diagnosis_results", "narrative")
    op.drop_column("diagnosis_results", "network_metrics")

    # ── Add new columns ──
    op.add_column(
        "diagnosis_results",
        sa.Column(
            "findings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "diagnosis_results",
        sa.Column(
            "recommendations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "diagnosis_results",
        sa.Column(
            "narrative_md",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "diagnosis_results",
        sa.Column(
            "structure_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column(
        "diagnosis_results",
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # ── Update status server_default ──
    op.alter_column(
        "diagnosis_results",
        "status",
        server_default="processing",
    )

    # ── Migrate existing status values ──
    op.execute(
        "UPDATE diagnosis_results SET status = 'processing' WHERE status = 'running'"
    )
    op.execute(
        "UPDATE diagnosis_results SET status = 'ready' WHERE status = 'completed'"
    )


def downgrade() -> None:
    # ── Restore status values ──
    op.execute(
        "UPDATE diagnosis_results SET status = 'running' WHERE status = 'processing'"
    )
    op.execute(
        "UPDATE diagnosis_results SET status = 'completed' WHERE status = 'ready'"
    )

    # ── Restore server_default ──
    op.alter_column(
        "diagnosis_results",
        "status",
        server_default="running",
    )

    # ── Drop new columns ──
    op.drop_column("diagnosis_results", "completed_at")
    op.drop_column("diagnosis_results", "structure_snapshot")
    op.drop_column("diagnosis_results", "narrative_md")
    op.drop_column("diagnosis_results", "recommendations")
    op.drop_column("diagnosis_results", "findings")

    # ── Restore legacy columns ──
    op.add_column(
        "diagnosis_results",
        sa.Column(
            "narrative",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column(
        "diagnosis_results",
        sa.Column(
            "network_metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )
