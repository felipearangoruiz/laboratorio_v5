"""Sprint 2.B Commit 5.5 — Tests de la migración context_notes→admin_notes.

Valida el SQL de la migración `20260422_0010_migrate_context_notes_to_admin_notes`:

1. Caso nuevo: Group con context_notes='legacy', Node con attrs={}. Tras
   correr el UPDATE, Node.attrs['admin_notes'] == 'legacy'.
2. Idempotencia: correr el UPDATE dos veces deja el mismo valor.
3. Prioridad del valor pre-existente: si attrs.admin_notes ya tiene valor
   no vacío, el UPDATE NO lo pisa (el modelo nuevo gana al viejo).
4. context_notes vacío o NULL: no genera cambios.

Estrategia: la migración ya corrió en el fixture `_postgres_url`
(alembic upgrade head). Creamos filas sintéticas en la sesión aislada y
re-ejecutamos el mismo SQL. Esto valida la lógica del UPDATE sin
depender de un teardown/up flujo de alembic.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import text
from sqlmodel import Session

from app.models.group import Group
from app.models.node import Node, NodeType
from app.models.organization import Organization


# El UPDATE exacto de la migración upgrade(); mantener sincronizado.
MIGRATION_SQL = """
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


def _mk_pair(
    session: Session,
    org_id,
    *,
    context_notes: str | None,
    initial_attrs: dict,
) -> tuple[Group, Node]:
    """Crea un Group y su Node espejo (mismo UUID) con los datos dados."""
    shared_id = uuid4()
    now = datetime.now(timezone.utc)
    g = Group(
        id=shared_id,
        organization_id=org_id,
        name="G",
        description="",
        tarea_general="",
        email="",
        area="",
        node_type="area",
        position_x=0.0,
        position_y=0.0,
        context_notes=context_notes,
        created_at=now,
    )
    n = Node(
        id=shared_id,
        organization_id=org_id,
        parent_node_id=None,
        type=NodeType.UNIT,
        name="G",
        position_x=0.0,
        position_y=0.0,
        attrs=initial_attrs,
        created_at=now,
    )
    session.add_all([g, n])
    session.flush()
    return g, n


def _admin_notes(session: Session, node_id) -> str | None:
    row = session.execute(
        text("SELECT attrs->>'admin_notes' AS v FROM nodes WHERE id = :id"),
        {"id": node_id},
    ).one()
    return row[0]


def test_migration_copies_context_notes_when_admin_notes_missing(session: Session):
    org = Organization(name="OrgCN", admin_id=None, created_at=datetime.now(timezone.utc))
    session.add(org)
    session.flush()

    _, node = _mk_pair(
        session, org.id, context_notes="legacy-text", initial_attrs={}
    )

    session.execute(text(MIGRATION_SQL))
    session.flush()

    assert _admin_notes(session, node.id) == "legacy-text"


def test_migration_is_idempotent(session: Session):
    org = Organization(name="OrgCN2", admin_id=None, created_at=datetime.now(timezone.utc))
    session.add(org)
    session.flush()

    _, node = _mk_pair(
        session, org.id, context_notes="foo", initial_attrs={}
    )

    session.execute(text(MIGRATION_SQL))
    session.flush()
    session.execute(text(MIGRATION_SQL))
    session.flush()

    assert _admin_notes(session, node.id) == "foo"


def test_migration_preserves_existing_admin_notes(session: Session):
    org = Organization(name="OrgCN3", admin_id=None, created_at=datetime.now(timezone.utc))
    session.add(org)
    session.flush()

    _, node = _mk_pair(
        session,
        org.id,
        context_notes="legacy",
        initial_attrs={"admin_notes": "modern"},
    )

    session.execute(text(MIGRATION_SQL))
    session.flush()

    # El valor escrito en el modelo nuevo gana al viejo.
    assert _admin_notes(session, node.id) == "modern"


def test_migration_noop_when_context_notes_empty(session: Session):
    org = Organization(name="OrgCN4", admin_id=None, created_at=datetime.now(timezone.utc))
    session.add(org)
    session.flush()

    _, node_null = _mk_pair(
        session, org.id, context_notes=None, initial_attrs={}
    )
    _, node_empty = _mk_pair(
        session, org.id, context_notes="", initial_attrs={}
    )

    session.execute(text(MIGRATION_SQL))
    session.flush()

    assert _admin_notes(session, node_null.id) is None
    assert _admin_notes(session, node_empty.id) is None
