"""add_interview_data_to_node_states

Revision ID: 20260421_0008
Revises: 20260421_0007
Create Date: 2026-04-21

Gap detectado en Sprint 1.2: NodeState no tenía columna interview_data
a pesar de estar especificada en MODEL_PHILOSOPHY.md §5.2.1 como parte
del contrato del estado "in_progress" ("hay interview_data parcial").

Esta migración agrega SOLO la columna faltante. No toca ninguna otra
tabla. El backfill de datos existentes se hace por separado mediante
backend/scripts/backfill_interview_data.py.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260421_0008"
down_revision = "20260421_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "node_states",
        sa.Column(
            "interview_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("node_states", "interview_data")
