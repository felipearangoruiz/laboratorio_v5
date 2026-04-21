"""fix group FK ondelete — interviews.group_id y processing_results.group_id

Revision ID: 20260420_0005
Revises: 20260420_0004
Create Date: 2026-04-20

Las FKs a groups.id en interviews y processing_results no tenían ondelete,
lo que causaba que el DELETE de un grupo fallara con IntegrityError de
PostgreSQL si existían entrevistas o resultados de procesamiento asociados
al grupo, aun después de pasar los guards del router (has_members, etc.).

Fix: cambiar ambas FKs a ON DELETE SET NULL para que la columna group_id
quede en NULL al borrar el grupo, en lugar de bloquear la operación.
"""

from alembic import op

revision = "20260420_0006"
down_revision = "20260420_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── interviews.group_id ───────────────────────────────────────────────
    op.drop_constraint(
        "fk_interviews_group_id_groups",
        "interviews",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_interviews_group_id_groups",
        "interviews",
        "groups",
        ["group_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ── processing_results.group_id ───────────────────────────────────────
    op.drop_constraint(
        "fk_processing_results_group_id_groups",
        "processing_results",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_processing_results_group_id_groups",
        "processing_results",
        "groups",
        ["group_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_processing_results_group_id_groups",
        "processing_results",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_processing_results_group_id_groups",
        "processing_results",
        "groups",
        ["group_id"],
        ["id"],
    )

    op.drop_constraint(
        "fk_interviews_group_id_groups",
        "interviews",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_interviews_group_id_groups",
        "interviews",
        "groups",
        ["group_id"],
        ["id"],
    )
