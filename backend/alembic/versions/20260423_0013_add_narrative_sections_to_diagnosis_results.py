"""Add narrative_sections to diagnosis_results (Sprint 5.A).

Columna JSONB nullable para la narrativa estructurada del Paso 4. Runs
históricos tienen NULL; el frontend maneja el caso.

Revision ID: 20260423_0013
Revises: 20260423_0012
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260423_0013"
down_revision = "20260423_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "diagnosis_results",
        sa.Column(
            "narrative_sections",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("diagnosis_results", "narrative_sections")
