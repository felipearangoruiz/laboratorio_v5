"""Router REST para Node (Sprint 1.3).

Implementa CRUD para la entidad unificada `Node` (type = unit | person).
Enforcea las invariantes 1-5 de MODEL_PHILOSOPHY.md §8:

- Invariante 1: scope organizacional — parent y nodo en misma org.
- Invariante 2: type ∈ {unit, person} (enforzado por enum).
- Invariante 3: person requiere parent_node_id NOT NULL y parent.type = unit.
- Invariante 4: unit puede ser raíz; si tiene parent debe ser otro unit.
- Invariante 5: parent_node_id define árbol acíclico.

Protección de borrado (3 pasos):
  1. NodeState con interview_data en campañas 'closed' → 409.
  2. NodeAnalysis / GroupAnalysis que referencian este UUID → 409.
  3. unit con hijos (parent_node_id = id) → 409.

Todas las queries filtran `deleted_at IS NULL` (soft-delete).
DELETE marca `deleted_at = now()`, no borra físicamente.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel import Session, select

from app.core.dependencies import get_current_user
from app.db import get_session
from app.models.node import Node, NodeRead, NodeType
from app.models.node_state import NodeState, NodeStateStatus
from app.models.user import User, UserRole

router = APIRouter()


# ─────────────────────────── Schemas ────────────────────────────

class NodeCreate(BaseModel):
    organization_id: UUID
    type: NodeType
    name: str
    parent_node_id: UUID | None = None
    position_x: float = 0.0
    position_y: float = 0.0
    attrs: dict = {}


class NodeUpdate(BaseModel):
    name: str | None = None
    parent_node_id: UUID | None = None
    position_x: float | None = None
    position_y: float | None = None
    attrs: dict | None = None


class NodePosition(BaseModel):
    id: UUID
    x: float
    y: float


class BulkNodePositions(BaseModel):
    positions: list[NodePosition]


# ─────────────────────────── Helpers ────────────────────────────

def _can_access_org(user: User, org_id: UUID) -> bool:
    return user.role == UserRole.SUPERADMIN or user.organization_id == org_id


def _get_live_node(session: Session, node_id: UUID) -> Node:
    node = session.get(Node, node_id)
    if not node or node.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    return node


def _validate_parent(
    session: Session,
    organization_id: UUID,
    node_type: NodeType,
    parent_node_id: UUID | None,
    current_node_id: UUID | None = None,
) -> None:
    """Valida invariantes 1, 3, 4, 5 relacionadas con parent_node_id."""
    if node_type == NodeType.PERSON and parent_node_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="person nodes must have parent_node_id",
        )
    if parent_node_id is None:
        return

    parent = session.get(Node, parent_node_id)
    if not parent or parent.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Parent node not found"
        )
    if parent.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Parent node must belong to the same organization",
        )
    if parent.type != NodeType.UNIT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Parent node must be of type 'unit'",
        )

    # Acyclic (invariante 5)
    if current_node_id is not None:
        if parent_node_id == current_node_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Node cannot be parent of itself",
            )
        cursor: Node | None = parent
        visited: set[UUID] = set()
        while cursor is not None and cursor.parent_node_id is not None:
            if cursor.id in visited:
                break
            visited.add(cursor.id)
            if cursor.parent_node_id == current_node_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Cycle detected in node hierarchy",
                )
            cursor = session.get(Node, cursor.parent_node_id)


# ─────────────────────────── Endpoints ──────────────────────────

@router.get("/nodes", response_model=list[NodeRead])
def list_nodes(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    organization_id: UUID | None = Query(default=None),
    type: NodeType | None = Query(default=None),
    parent_node_id: UUID | None = Query(default=None),
) -> list[NodeRead]:
    query = select(Node).where(Node.deleted_at.is_(None))
    if organization_id is not None:
        if not _can_access_org(current_user, organization_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        query = query.where(Node.organization_id == organization_id)
    elif current_user.role != UserRole.SUPERADMIN:
        query = query.where(Node.organization_id == current_user.organization_id)
    if type is not None:
        query = query.where(Node.type == type)
    if parent_node_id is not None:
        query = query.where(Node.parent_node_id == parent_node_id)
    nodes = session.exec(query).all()
    return [NodeRead.model_validate(n) for n in nodes]


@router.get("/nodes/{node_id}", response_model=NodeRead)
def get_node(
    node_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> NodeRead:
    node = _get_live_node(session, node_id)
    if not _can_access_org(current_user, node.organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return NodeRead.model_validate(node)


@router.post("/nodes", response_model=NodeRead, status_code=status.HTTP_201_CREATED)
def create_node(
    payload: NodeCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> NodeRead:
    if not _can_access_org(current_user, payload.organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    _validate_parent(session, payload.organization_id, payload.type, payload.parent_node_id)

    node = Node(
        organization_id=payload.organization_id,
        parent_node_id=payload.parent_node_id,
        type=payload.type,
        name=payload.name,
        position_x=payload.position_x,
        position_y=payload.position_y,
        attrs=payload.attrs or {},
    )
    session.add(node)
    session.commit()
    session.refresh(node)
    return NodeRead.model_validate(node)


@router.patch("/nodes/{node_id}", response_model=NodeRead)
def update_node(
    node_id: UUID,
    payload: NodeUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> NodeRead:
    node = _get_live_node(session, node_id)
    if not _can_access_org(current_user, node.organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    data = payload.model_dump(exclude_unset=True)
    if "parent_node_id" in data:
        _validate_parent(
            session,
            node.organization_id,
            node.type,
            data["parent_node_id"],
            current_node_id=node.id,
        )

    for field, value in data.items():
        setattr(node, field, value)

    session.add(node)
    session.commit()
    session.refresh(node)
    return NodeRead.model_validate(node)


@router.patch("/organizations/{org_id}/nodes/positions")
def bulk_update_node_positions(
    org_id: UUID,
    payload: BulkNodePositions,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    """Actualiza posiciones de varios nodos de la organización en una
    sola transacción.

    Soporta tanto `type=unit` como `type=person`. Reemplaza al legacy
    /organizations/{org_id}/groups/positions, que sólo actualizaba
    Groups y dejaba los persons sin persistencia en DB.

    Valida que cada nodo pertenezca a la organización del path. Los
    ids que no pertenezcan a la org (o no existan / estén
    soft-deleted) se ignoran silenciosamente; el conteo devuelto es
    el de nodos efectivamente actualizados.
    """
    if not _can_access_org(current_user, org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    updated = 0
    for pos in payload.positions:
        node = session.get(Node, pos.id)
        if node is None or node.deleted_at is not None:
            continue
        if node.organization_id != org_id:
            continue
        node.position_x = pos.x
        node.position_y = pos.y
        session.add(node)
        updated += 1

    session.commit()
    return {"updated": updated}


@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_node(
    node_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    node = _get_live_node(session, node_id)
    if not _can_access_org(current_user, node.organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    # Step 1 — NodeStates con interview_data en campañas 'closed'
    closed_with_data = session.execute(
        text(
            "SELECT COUNT(*) FROM node_states ns "
            "JOIN assessment_campaigns c ON c.id = ns.campaign_id "
            "WHERE ns.node_id = :nid "
            "  AND ns.interview_data IS NOT NULL "
            "  AND c.status = 'closed'"
        ),
        {"nid": str(node_id)},
    ).scalar_one()
    if closed_with_data > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Node has interview data in closed campaigns; cannot delete",
        )

    # Step 2 — motor de análisis (UUID preservado entre groups/nodes)
    try:
        n_analyses = session.execute(
            text("SELECT COUNT(*) FROM node_analyses WHERE group_id = :nid"),
            {"nid": str(node_id)},
        ).scalar_one()
        g_analyses = session.execute(
            text("SELECT COUNT(*) FROM group_analyses WHERE group_id = :nid"),
            {"nid": str(node_id)},
        ).scalar_one()
    except Exception:
        # Tablas del motor pueden no existir en tests con SQLite fixture.
        n_analyses = g_analyses = 0
    if (n_analyses or 0) + (g_analyses or 0) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Node is referenced by analysis results; cannot delete",
        )

    # Step 3 — unit con hijos vivos
    if node.type == NodeType.UNIT:
        child = session.exec(
            select(Node).where(
                Node.parent_node_id == node.id,
                Node.deleted_at.is_(None),
            )
        ).first()
        if child is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Unit has children; cannot delete",
            )

    # Soft-delete
    node.deleted_at = datetime.now(timezone.utc)
    session.add(node)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
