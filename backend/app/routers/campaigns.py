"""Router REST para AssessmentCampaign (Sprint 1.3).

Enforcea invariante 11: una sola campaña `active` por organización simultáneamente
(draft y closed pueden coexistir sin restricción).

Protección de borrado: si alguna NodeState de la campaña tiene interview_data,
la campaña no se puede DELETE — se debe cerrar vía PATCH (status='closed').
Esto preserva trazabilidad histórica de respuestas.
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
from app.models.campaign import AssessmentCampaign, AssessmentCampaignRead, CampaignStatus
from app.models.node_state import NodeState
from app.models.user import User, UserRole

router = APIRouter()


# ─────────────────────────── Schemas ────────────────────────────

class CampaignCreate(BaseModel):
    organization_id: UUID
    name: str
    status: CampaignStatus = CampaignStatus.DRAFT
    started_at: datetime | None = None


class CampaignUpdate(BaseModel):
    name: str | None = None
    status: CampaignStatus | None = None
    started_at: datetime | None = None
    closed_at: datetime | None = None


# ─────────────────────────── Helpers ────────────────────────────

def _can_access_org(user: User, org_id: UUID) -> bool:
    return user.role == UserRole.SUPERADMIN or user.organization_id == org_id


def _require_unique_active(
    session: Session,
    organization_id: UUID,
    exclude_id: UUID | None = None,
) -> None:
    """Invariante 11: a lo sumo una 'active' por organización."""
    query = select(AssessmentCampaign).where(
        AssessmentCampaign.organization_id == organization_id,
        AssessmentCampaign.status == CampaignStatus.ACTIVE,
    )
    if exclude_id is not None:
        query = query.where(AssessmentCampaign.id != exclude_id)
    existing = session.exec(query).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Organization already has an active campaign",
        )


# ─────────────────────────── Endpoints ──────────────────────────

@router.get("/campaigns", response_model=list[AssessmentCampaignRead])
def list_campaigns(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    organization_id: UUID | None = Query(default=None),
    status_filter: CampaignStatus | None = Query(default=None, alias="status"),
) -> list[AssessmentCampaignRead]:
    query = select(AssessmentCampaign)
    if organization_id is not None:
        if not _can_access_org(current_user, organization_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        query = query.where(AssessmentCampaign.organization_id == organization_id)
    elif current_user.role != UserRole.SUPERADMIN:
        query = query.where(AssessmentCampaign.organization_id == current_user.organization_id)
    if status_filter is not None:
        query = query.where(AssessmentCampaign.status == status_filter)
    campaigns = session.exec(query).all()
    return [AssessmentCampaignRead.model_validate(c) for c in campaigns]


@router.get("/campaigns/{campaign_id}", response_model=AssessmentCampaignRead)
def get_campaign(
    campaign_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AssessmentCampaignRead:
    campaign = session.get(AssessmentCampaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if not _can_access_org(current_user, campaign.organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return AssessmentCampaignRead.model_validate(campaign)


@router.post("/campaigns", response_model=AssessmentCampaignRead, status_code=status.HTTP_201_CREATED)
def create_campaign(
    payload: CampaignCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AssessmentCampaignRead:
    if not _can_access_org(current_user, payload.organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    if payload.status == CampaignStatus.ACTIVE:
        _require_unique_active(session, payload.organization_id)

    campaign = AssessmentCampaign(
        organization_id=payload.organization_id,
        created_by_user_id=current_user.id,
        name=payload.name,
        status=payload.status,
        started_at=payload.started_at,
    )
    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    return AssessmentCampaignRead.model_validate(campaign)


@router.patch("/campaigns/{campaign_id}", response_model=AssessmentCampaignRead)
def update_campaign(
    campaign_id: UUID,
    payload: CampaignUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> AssessmentCampaignRead:
    campaign = session.get(AssessmentCampaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if not _can_access_org(current_user, campaign.organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    data = payload.model_dump(exclude_unset=True)
    if data.get("status") == CampaignStatus.ACTIVE and campaign.status != CampaignStatus.ACTIVE:
        _require_unique_active(session, campaign.organization_id, exclude_id=campaign.id)

    # Auto-stamp closed_at when transitioning to 'closed' if caller didn't set it.
    if (
        data.get("status") == CampaignStatus.CLOSED
        and campaign.status != CampaignStatus.CLOSED
        and "closed_at" not in data
    ):
        data["closed_at"] = datetime.now(timezone.utc)

    for field, value in data.items():
        setattr(campaign, field, value)

    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    return AssessmentCampaignRead.model_validate(campaign)


@router.delete("/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(
    campaign_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    campaign = session.get(AssessmentCampaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if not _can_access_org(current_user, campaign.organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    has_data = session.exec(
        select(NodeState).where(
            NodeState.campaign_id == campaign_id,
            NodeState.interview_data.is_not(None),
        )
    ).first()
    if has_data is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign has NodeStates with interview_data; close via PATCH instead of DELETE",
        )

    # Hard delete: no hay data de campaña. Borra también NodeStates vacíos asociados.
    empty_states = session.exec(
        select(NodeState).where(NodeState.campaign_id == campaign_id)
    ).all()
    for ns in empty_states:
        session.delete(ns)
    session.delete(campaign)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
