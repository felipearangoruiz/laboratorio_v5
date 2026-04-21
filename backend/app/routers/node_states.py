"""Router REST para NodeState (Sprint 1.3).

Enforcea invariantes 1 y 10 de MODEL_PHILOSOPHY.md §8:

- Invariante 1: node y campaign deben pertenecer a la misma organización.
- Invariante 10: UNIQUE (node_id, campaign_id) — un nodo tiene a lo sumo un
  estado por campaña. Violación → 409.

Protección de borrado: si el NodeState tiene interview_data y la campaña está
'closed', no se puede DELETE (respuestas históricas son inmutables).
"""
from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.dependencies import get_current_user
from app.db import get_session
from app.models.campaign import AssessmentCampaign, CampaignStatus
from app.models.node import Node
from app.models.node_state import NodeState, NodeStateRead, NodeStateStatus
from app.models.user import User, UserRole

router = APIRouter()


# ─────────────────────────── Schemas ────────────────────────────

class NodeStateCreate(BaseModel):
    node_id: UUID
    campaign_id: UUID
    email_assigned: str | None = None
    role_label: str | None = None
    context_notes: str | None = None
    respondent_token: str | None = None
    status: NodeStateStatus = NodeStateStatus.INVITED
    interview_data: dict[str, Any] | None = None


class NodeStateUpdate(BaseModel):
    email_assigned: str | None = None
    role_label: str | None = None
    context_notes: str | None = None
    respondent_token: str | None = None
    status: NodeStateStatus | None = None
    interview_data: dict[str, Any] | None = None


# ─────────────────────────── Helpers ────────────────────────────

def _can_access_org(user: User, org_id: UUID) -> bool:
    return user.role == UserRole.SUPERADMIN or user.organization_id == org_id


def _resolve_org(
    session: Session,
    node_id: UUID,
    campaign_id: UUID,
) -> UUID:
    """Invariante 1: node y campaign misma org. Devuelve org_id común."""
    node = session.get(Node, node_id)
    if not node or node.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    campaign = session.get(AssessmentCampaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if node.organization_id != campaign.organization_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Node and campaign must belong to the same organization",
        )
    return node.organization_id


# ─────────────────────────── Endpoints ──────────────────────────

@router.get("/node-states", response_model=list[NodeStateRead])
def list_node_states(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    node_id: UUID | None = Query(default=None),
    campaign_id: UUID | None = Query(default=None),
    status_filter: NodeStateStatus | None = Query(default=None, alias="status"),
) -> list[NodeStateRead]:
    query = select(NodeState)
    if node_id is not None:
        query = query.where(NodeState.node_id == node_id)
    if campaign_id is not None:
        query = query.where(NodeState.campaign_id == campaign_id)
    if status_filter is not None:
        query = query.where(NodeState.status == status_filter)

    states = session.exec(query).all()
    # Org-scoped filter via node.organization_id
    if current_user.role != UserRole.SUPERADMIN:
        allowed: list[NodeState] = []
        for ns in states:
            node = session.get(Node, ns.node_id)
            if node is not None and node.organization_id == current_user.organization_id:
                allowed.append(ns)
        states = allowed
    return [NodeStateRead.model_validate(ns) for ns in states]


@router.get("/node-states/{node_state_id}", response_model=NodeStateRead)
def get_node_state(
    node_state_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> NodeStateRead:
    ns = session.get(NodeState, node_state_id)
    if not ns:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NodeState not found")
    node = session.get(Node, ns.node_id)
    if node is None or not _can_access_org(current_user, node.organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return NodeStateRead.model_validate(ns)


@router.post("/node-states", response_model=NodeStateRead, status_code=status.HTTP_201_CREATED)
def create_node_state(
    payload: NodeStateCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> NodeStateRead:
    org_id = _resolve_org(session, payload.node_id, payload.campaign_id)
    if not _can_access_org(current_user, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    # Pre-check unicidad (invariante 10); IntegrityError es el fallback.
    existing = session.exec(
        select(NodeState).where(
            NodeState.node_id == payload.node_id,
            NodeState.campaign_id == payload.campaign_id,
        )
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="NodeState for this (node_id, campaign_id) already exists",
        )

    ns = NodeState(
        node_id=payload.node_id,
        campaign_id=payload.campaign_id,
        email_assigned=payload.email_assigned,
        role_label=payload.role_label,
        context_notes=payload.context_notes,
        respondent_token=payload.respondent_token,
        status=payload.status,
        interview_data=payload.interview_data,
    )
    session.add(ns)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="NodeState unique constraint violated",
        )
    session.refresh(ns)
    return NodeStateRead.model_validate(ns)


@router.patch("/node-states/{node_state_id}", response_model=NodeStateRead)
def update_node_state(
    node_state_id: UUID,
    payload: NodeStateUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> NodeStateRead:
    ns = session.get(NodeState, node_state_id)
    if not ns:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NodeState not found")
    node = session.get(Node, ns.node_id)
    if node is None or not _can_access_org(current_user, node.organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(ns, field, value)

    session.add(ns)
    session.commit()
    session.refresh(ns)
    return NodeStateRead.model_validate(ns)


@router.delete("/node-states/{node_state_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_node_state(
    node_state_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    ns = session.get(NodeState, node_state_id)
    if not ns:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NodeState not found")
    node = session.get(Node, ns.node_id)
    if node is None or not _can_access_org(current_user, node.organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    if ns.interview_data is not None:
        campaign = session.get(AssessmentCampaign, ns.campaign_id)
        if campaign is not None and campaign.status == CampaignStatus.CLOSED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="NodeState has interview_data in a closed campaign; cannot delete",
            )

    session.delete(ns)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
