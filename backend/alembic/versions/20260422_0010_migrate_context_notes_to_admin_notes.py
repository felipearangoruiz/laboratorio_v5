"""Migrate Group.context_notes → Node.attrs.admin_notes.

Sprint 2.B Commit 5.5. One-shot data migration that copies legacy
context_notes (solo existe en Group; Member NO tiene esta columna) al
nuevo key attrs.admin_notes del Node espejo correspondiente.

Idempotente: si attrs.admin_notes ya existe y tiene valor no vacío, se
preserva. El valor escrito en el modelo nuevo (PATCH /nodes) gana sobre
lo heredado del modelo viejo.

Downgrade no-op: revertir destructivamente (borrar admin_notes) tiene
más riesgo que beneficio. Los datos legacy permanecen en
groups.context_notes; admin_notes sobrevive en attrs.

Revision ID: 20260422_0010
Revises: 20260421_0009
"""
from alembic import op


# revision identifiers
revision = "20260422_0010"
down_revision = "20260421_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Copiar groups.context_notes → nodes.attrs.admin_notes solo cuando el
    # key admin_notes no existe aún o está vacío. Así respetamos lo ya
    # escrito vía PATCH /nodes por el frontend nuevo.
    op.execute(
        """
        UPDATE nodes
        SET attrs = jsonb_set(
            COALESCE(nodes.attrs, '{}'::jsonb),
            '{admin_notes}',
            to_jsonb(g.context_notes),
            true
        )
        FROM groups g
        WHERE nodes.id = g.id
          AND g.context_notes IS NOT NULL
          AND g.context_notes <> ''
          AND (
            nodes.attrs IS NULL
            OR NOT (nodes.attrs ? 'admin_notes')
            OR nodes.attrs->>'admin_notes' IS NULL
            OR nodes.attrs->>'admin_notes' = ''
          )
        """
    )

    # Member.context_notes NO existe en el esquema actual (verificado en
    # backend/app/models/member.py al momento de escribir esta migración).
    # Si se agregara en el futuro, espejar el UPDATE anterior con JOIN a
    # members.


def downgrade() -> None:
    # No-op intencional. Ver Sprint 2.B Commit 5.5: la reversión
    # destructiva (borrar admin_notes) tiene más riesgo que beneficio.
    # Los datos legacy permanecen en groups.context_notes.
    pass
