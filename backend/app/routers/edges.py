"""Router REST para Edge (Sprint 1.3).

Enforcea invariantes 1, 6, 7, 8, 13 de MODEL_PHILOSOPHY.md §8:

- Invariante 1: source, target y edge misma organization_id.
- Invariante 6: source y target type='unit' (no hay edges con persons).
- Invariante 7: source != target; no duplicados en (source, target, edge_type).
- Invariante 8: edge_type ∈ {lateral, process} (enforzado por enum).
- Invariante 13: edge_type='process' requiere edge_metadata['order'] entero positivo.

Sin protecciones especiales de borrado (soft-delete simple).
Filtran `deleted_at IS NULL`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.dependencies import get_current_user
from app.db import get_session
from app.models.edge import Edge, EdgeRead, EdgeType
from app.models.node import Node, NodeType
from app.models.user import User, UserRole

router = APIRouter()


# ─────────────────────────── Schemas ────────────────────────────

class EdgeCreate(BaseModel):
    organization_id: UUID
    source_node_id: UUID
    target_node_id: UUID
    edge_type: EdgeType
    edge_metadata: dict = {}


class EdgeUpdate(BaseModel):
    edge_type: EdgeType | None = None
    edge_metadata: dict | None = None


# ─────────────────────────── Helpers ────────────────────────────

def _can_access_org(user: User, org_id: UUID) -> bool:
    return user.role == UserRole.SUPERADMIN or user.organization_id == org_id


def _get_live_edge(session: Session, edge_id: UUID) -> Edge:
    edge = session.get(Edge, edge_id)
    if not edge or edge.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edge not found")
    return edge


def _validate_process_metadata(edge_type: EdgeType, metadata: dict) -> None:
    """Invariante 13: process edges requieren 'order' entero positivo."""
    if edge_type != EdgeType.PROCESS:
        return
    order = metadata.get("order") if isinstance(metadata, dict) else None
    if not isinstance(order, int) or isinstance(order, bool) or order < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="process edges require edge_metadata.order as positive integer",
        )


def _validate_endpoints(
    session: Session,
    organization_id: UUID,
    source_id: UUID,
    target_id: UUID,
) -> None:
    """Invariantes 1, 6, 7 (parte del self-loop)."""
    if source_id == target_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Edge source and target must differ",
        )
    source = session.get(Node, source_id)
    target = session.get(Node, target_id)
    for role, node in (("source", source), ("target", target)):
        if not node or node.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Edge {role} node not found",
            )
        if node.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Edge {role} node must belong to the same organization",
            )
        if node.type != NodeType.UNIT:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Edge {role} node must be of type 'unit'",
            )


def _check_duplicate(
    session: Session,
    source_id: UUID,
    target_id: UUID,
    edge_type: EdgeType,
    exclude_id: UUID | None = None,
) -> None:
    query = select(Edge).where(
        Edge.source_node_id == source_id,
        Edge.target_node_id == target_id,
        Edge.edge_type == edge_type,
        Edge.deleted_at.is_(None),
    )
    if exclude_id is not None:
        query = query.where(Edge.id != exclude_id)
    if session.exec(query).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An edge with the same (source, target, edge_type) already exists",
        )


# ─────────────────────────── Endpoints ──────────────────────────

@router.get("/edges", response_model=list[EdgeRead])
def list_edges(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    organization_id: UUID | None = Query(default=None),
    source_node_id: UUID | None = Query(default=None),
    target_node_id: UUID | None = Query(default=None),
    edge_type: EdgeType | None = Query(default=None),
) -> list[EdgeRead]:
    query = select(Edge).where(Edge.deleted_at.is_(None))
    if organization_id is not None:
        if not _can_access_org(current_user, organization_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        query = query.where(Edge.organization_id == organization_id)
    elif current_user.role != UserRole.SUPERADMIN:
        query = query.where(Edge.organization_id == current_user.organization_id)
    if source_node_id is not None:
        query = query.where(Edge.source_node_id == source_node_id)
    if target_node_id is not None:
        query = query.where(Edge.target_node_id == target_node_id)
    if edge_type is not None:
        query = query.where(Edge.edge_type == edge_type)
    edges = session.exec(query).all()
    return [EdgeRead.model_validate(e) for e in edges]


@router.get("/edges/{edge_id}", response_model=EdgeRead)
def get_edge(
    edge_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> EdgeRead:
    edge = _get_live_edge(session, edge_id)
    if not _can_access_org(current_user, edge.organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return EdgeRead.model_validate(edge)


@router.post("/edges", response_model=EdgeRead, status_code=status.HTTP_201_CREATED)
def create_edge(
    payload: EdgeCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> EdgeRead:
    if not _can_access_org(current_user, payload.organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    _validate_endpoints(session, payload.organization_id, payload.source_node_id, payload.target_node_id)
    _validate_process_metadata(payload.edge_type, payload.edge_metadata or {})
    _check_duplicate(session, payload.source_node_id, payload.target_node_id, payload.edge_type)

    edge = Edge(
        organization_id=payload.organization_id,
        source_node_id=payload.source_node_id,
        target_node_id=payload.target_node_id,
        edge_type=payload.edge_type,
        edge_metadata=payload.edge_metadata or {},
    )
    session.add(edge)
    session.commit()
    session.refresh(edge)
    return EdgeRead.model_validate(edge)


@router.patch("/edges/{edge_id}", response_model=EdgeRead)
def update_edge(
    edge_id: UUID,
    payload: EdgeUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> EdgeRead:
    edge = _get_live_edge(session, edge_id)
    if not _can_access_org(current_user, edge.organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    data = payload.model_dump(exclude_unset=True)
    new_type = data.get("edge_type", edge.edge_type)
    new_metadata = data.get("edge_metadata", edge.edge_metadata or {})
    _validate_process_metadata(new_type, new_metadata)

    if "edge_type" in data and data["edge_type"] != edge.edge_type:
        _check_duplicate(
            session,
            edge.source_node_id,
            edge.target_node_id,
            new_type,
            exclude_id=edge.id,
        )

    for field, value in data.items():
        setattr(edge, field, value)

    session.add(edge)
    session.commit()
    session.refresh(edge)
    return EdgeRead.model_validate(edge)


@router.delete("/edges/{edge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_edge(
    edge_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    edge = _get_live_edge(session, edge_id)
    if not _can_access_org(current_user, edge.organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    edge.deleted_at = datetime.now(timezone.utc)
    session.add(edge)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
