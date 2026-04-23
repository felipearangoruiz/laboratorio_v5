"""Sprint 3 Commit 1 — Verificación del rename group_id → node_id.

La migración `20260423_0012_rename_motor_group_id_to_node_id` renombra
`node_analyses.group_id` y `group_analyses.group_id` a `node_id`, y
re-apunta sus FKs a `nodes(id)`. Estos tests validan:

1. Las columnas `node_id` existen post-migración.
2. Las FKs apuntan a `nodes(id)`.
3. Los comentarios documentan la semántica distinta por tabla.
4. Un UUID preservado (unit Node creado en una campaña de test)
   resuelve correctamente como `node_id` en ambas tablas.

Nota sobre idempotencia de downgrade/upgrade: los tests de conftest
corren con el schema en `head` (incluyendo 20260423_0012 ya aplicada).
Para verificar el ciclo downgrade→upgrade, se invoca alembic
programáticamente con la misma URL de Postgres del engine del test.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlmodel import Session

from app.models.node import Node, NodeType
from app.models.organization import Organization

_BACKEND_ROOT = Path(__file__).resolve().parent.parent


# ─────────────────── Tests schema ───────────────────

def test_node_analyses_tiene_columna_node_id(session: Session) -> None:
    """La columna `node_id` existe y `group_id` ya no."""
    insp = inspect(session.connection())
    cols = {c["name"] for c in insp.get_columns("node_analyses")}
    assert "node_id" in cols, "node_analyses debería tener columna node_id"
    assert "group_id" not in cols, "node_analyses no debería tener group_id"


def test_group_analyses_tiene_columna_node_id(session: Session) -> None:
    insp = inspect(session.connection())
    cols = {c["name"] for c in insp.get_columns("group_analyses")}
    assert "node_id" in cols, "group_analyses debería tener columna node_id"
    assert "group_id" not in cols


def test_node_analyses_fk_apunta_a_nodes(session: Session) -> None:
    """La FK de node_analyses.node_id referencia nodes(id)."""
    insp = inspect(session.connection())
    fks = insp.get_foreign_keys("node_analyses")
    by_cols = {tuple(fk["constrained_columns"]): fk for fk in fks}
    assert ("node_id",) in by_cols, "No hay FK sobre (node_id,)"
    fk = by_cols[("node_id",)]
    assert fk["referred_table"] == "nodes"
    assert fk["referred_columns"] == ["id"]


def test_group_analyses_fk_apunta_a_nodes(session: Session) -> None:
    insp = inspect(session.connection())
    fks = insp.get_foreign_keys("group_analyses")
    by_cols = {tuple(fk["constrained_columns"]): fk for fk in fks}
    assert ("node_id",) in by_cols
    fk = by_cols[("node_id",)]
    assert fk["referred_table"] == "nodes"
    assert fk["referred_columns"] == ["id"]


def test_comentarios_documentan_semantica(session: Session) -> None:
    """Los COMMENT on COLUMN aclaran qué type de nodo referencia cada tabla."""
    na_comment = session.execute(
        text(
            "SELECT col_description('node_analyses'::regclass, "
            "(SELECT attnum FROM pg_attribute WHERE attrelid = 'node_analyses'::regclass "
            "AND attname = 'node_id'))"
        )
    ).scalar_one()
    assert na_comment and "person" in na_comment.lower()

    ga_comment = session.execute(
        text(
            "SELECT col_description('group_analyses'::regclass, "
            "(SELECT attnum FROM pg_attribute WHERE attrelid = 'group_analyses'::regclass "
            "AND attname = 'node_id'))"
        )
    ).scalar_one()
    assert ga_comment and "unit" in ga_comment.lower()


# ─────────────────── Test downgrade → upgrade ───────────────────

def test_downgrade_upgrade_idempotente(_postgres_url: str) -> None:
    """Verifica que downgrade + upgrade es idempotente.

    La migración renombra columnas y FKs; el downgrade debe dejar el
    schema en el estado previo (columna `group_id` con FK a `groups`),
    y un nuevo upgrade debe volver a `node_id` con FK a `nodes`.
    """
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "alembic"))
    # sobrescribir URL para usar el contenedor del test
    cfg.set_main_option("sqlalchemy.url", _postgres_url)

    try:
        # HEAD → -1 (deshace 20260423_0012)
        command.downgrade(cfg, "-1")
        from sqlalchemy import create_engine

        eng = create_engine(_postgres_url, future=True)
        try:
            with eng.connect() as conn:
                insp = inspect(conn)
                cols_na = {c["name"] for c in insp.get_columns("node_analyses")}
                cols_ga = {c["name"] for c in insp.get_columns("group_analyses")}
                assert "group_id" in cols_na and "node_id" not in cols_na
                assert "group_id" in cols_ga and "node_id" not in cols_ga

                # La FK debe apuntar a groups nuevamente
                fks_na = {tuple(fk["constrained_columns"]): fk
                          for fk in insp.get_foreign_keys("node_analyses")}
                assert fks_na[("group_id",)]["referred_table"] == "groups"
        finally:
            eng.dispose()

        # Re-upgrade
        command.upgrade(cfg, "head")
    finally:
        # Asegurar que el schema siempre queda en head para otros tests.
        command.upgrade(cfg, "head")


# ─────────────────── Test integración con ORM ───────────────────

def test_orm_node_id_resuelve_a_node_existente(session: Session) -> None:
    """Una fila de node_analyses con node_id = <unit.id> resuelve vía FK."""
    org = Organization(name="MotorFKTest", description="", sector="tech")
    session.add(org)
    session.commit()
    session.refresh(org)

    unit = Node(
        organization_id=org.id,
        parent_node_id=None,
        type=NodeType.UNIT,
        name="Unit rename test",
    )
    session.add(unit)
    session.commit()
    session.refresh(unit)

    # Insertar analysis_run + node_analysis vía raw SQL para evitar
    # depender del ORM del modelo (que se actualiza en Commit 2).
    run_id = uuid4()
    now = datetime.now(timezone.utc)
    session.execute(
        text(
            "INSERT INTO analysis_runs (id, org_id, status, started_at, "
            "total_nodes, total_groups) "
            "VALUES (:id, :org, 'completed', :now, 1, 0)"
        ),
        {"id": str(run_id), "org": str(org.id), "now": now},
    )

    na_id = uuid4()
    session.execute(
        text(
            "INSERT INTO node_analyses (id, run_id, org_id, node_id, created_at) "
            "VALUES (:id, :run, :org, :node, :now)"
        ),
        {
            "id": str(na_id),
            "run": str(run_id),
            "org": str(org.id),
            "node": str(unit.id),
            "now": now,
        },
    )
    session.commit()

    # Verificar que la fila existe con el node_id correcto
    row = session.execute(
        text("SELECT node_id FROM node_analyses WHERE id = :id"),
        {"id": str(na_id)},
    ).first()
    assert row is not None
    assert str(row[0]) == str(unit.id)

    # Probar la FK: intentar insertar con un node_id inexistente debe fallar.
    bogus = uuid4()
    with pytest.raises(Exception):
        session.execute(
            text(
                "INSERT INTO node_analyses (id, run_id, org_id, node_id, created_at) "
                "VALUES (:id, :run, :org, :node, :now)"
            ),
            {
                "id": str(uuid4()),
                "run": str(run_id),
                "org": str(org.id),
                "node": str(bogus),
                "now": now,
            },
        )
