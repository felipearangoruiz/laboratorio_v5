"""Rename motor group_id → node_id and re-point FKs to nodes.id

Sprint 3 Commit 1. Las tablas `node_analyses` y `group_analyses` fueron
creadas en `20260420_0005` con una columna `group_id UUID FK groups(id)`,
herencia del modelo pre-refactor. Desde Sprint 1.2 los UUIDs de la antigua
tabla `groups` están preservados en la nueva tabla `nodes` (misma id),
así que semánticamente esa columna ya referenciaba `nodes.id` sin
cambiar. Este sprint formaliza ese estado:

- Renombra `node_analyses.group_id → node_id`.
- Renombra `group_analyses.group_id → node_id`.
- Re-apunta las FKs a `nodes(id)` en lugar de `groups(id)`.
- Deja comentarios SQL documentando la semántica distinta por tabla:
    * `node_analyses.node_id` → `nodes.type='person'` (respondiente).
    * `group_analyses.node_id` → `nodes.type='unit'` (área/grupo).

`findings.node_ids` y `recommendations.node_ids` son columnas jsonb que
contienen arrays de UUIDs. No requieren rename físico — la aclaración
semántica queda en docs/MOTOR_ANALISIS.md.

Pre-check integrado: aborta si hay group_id huérfanos en node_analyses
o group_analyses (es decir, que no existan en `nodes`). El diagnóstico
read-only previo confirmó 0 huérfanos en producción antes de correr.

Revision ID: 20260423_0012
Revises: 20260422_0011
"""
from __future__ import annotations

from alembic import op

revision = "20260423_0012"
down_revision = "20260422_0011"
branch_labels = None
depends_on = None


def _count_orphans(conn, table: str) -> int:
    row = conn.exec_driver_sql(
        f"""
        SELECT COUNT(*)
        FROM {table} t
        LEFT JOIN nodes n ON n.id = t.group_id
        WHERE n.id IS NULL
        """
    ).fetchone()
    return int(row[0]) if row else 0


def upgrade() -> None:
    # ── Pre-check de integridad ──────────────────────────────────────
    conn = op.get_bind()
    na_orphans = _count_orphans(conn, "node_analyses")
    ga_orphans = _count_orphans(conn, "group_analyses")
    if na_orphans or ga_orphans:
        raise RuntimeError(
            f"Rename abortado: group_ids huérfanos detectados "
            f"(node_analyses={na_orphans}, group_analyses={ga_orphans}). "
            "Un group_id huérfano significa que la columna apunta a un UUID "
            "que no existe en `nodes`. Revisar con las queries del sprint "
            "de diagnóstico antes de re-aplicar."
        )

    # ── node_analyses ────────────────────────────────────────────────
    op.drop_constraint(
        "node_analyses_group_id_fkey", "node_analyses", type_="foreignkey"
    )
    op.alter_column("node_analyses", "group_id", new_column_name="node_id")
    op.create_foreign_key(
        "node_analyses_node_id_fkey",
        "node_analyses",
        "nodes",
        ["node_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.execute(
        "COMMENT ON COLUMN node_analyses.node_id IS "
        "'FK a nodes.id. Referencia semánticamente al respondiente "
        "(nodes.type = ''person''). Paso 1 del pipeline.'"
    )

    # ── group_analyses ───────────────────────────────────────────────
    op.drop_constraint(
        "group_analyses_group_id_fkey", "group_analyses", type_="foreignkey"
    )
    op.alter_column("group_analyses", "group_id", new_column_name="node_id")
    op.create_foreign_key(
        "group_analyses_node_id_fkey",
        "group_analyses",
        "nodes",
        ["node_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.execute(
        "COMMENT ON COLUMN group_analyses.node_id IS "
        "'FK a nodes.id. Referencia a un nodo de tipo unit "
        "(nodes.type = ''unit''). Paso 2 del pipeline.'"
    )


def downgrade() -> None:
    # Reverso exacto: drop FKs, rename node_id → group_id, recrear FK a groups.
    op.execute("COMMENT ON COLUMN group_analyses.node_id IS NULL")
    op.drop_constraint(
        "group_analyses_node_id_fkey", "group_analyses", type_="foreignkey"
    )
    op.alter_column("group_analyses", "node_id", new_column_name="group_id")
    op.create_foreign_key(
        "group_analyses_group_id_fkey",
        "group_analyses",
        "groups",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.execute("COMMENT ON COLUMN node_analyses.node_id IS NULL")
    op.drop_constraint(
        "node_analyses_node_id_fkey", "node_analyses", type_="foreignkey"
    )
    op.alter_column("node_analyses", "node_id", new_column_name="group_id")
    op.create_foreign_key(
        "node_analyses_group_id_fkey",
        "node_analyses",
        "groups",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
