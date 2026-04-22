"""COMPATIBILITY LAYER — Sprint 1.4

Este router es legacy. Sirve la experiencia del entrevistado vía token
(`/entrevista/{token}`). Cada escritura sobre `interviews`/`members` se
espeja sobre `node_states` dentro de la misma transacción, conservando
UUIDs.

Convención de Campaign: los interviews legacy se espejan contra el
NodeState de la Campaign llamada "Diagnóstico Inicial" de la org del
Member. Si esa Campaign no existe (caso anómalo post-migración), se
crea on-the-fly con `status=active` y `created_by_user_id=NULL`.

Mapeo de estado Member → NodeState:
  - PENDING     → INVITED
  - IN_PROGRESS → IN_PROGRESS
  - COMPLETED   → COMPLETED
  - EXPIRED     → SKIPPED

El endpoint público NO está marcado `deprecated=True` en el decorator
porque lo consume el frontend del entrevistado directamente; la marca
deprecated se expone en la versión autenticada (`/interviews`).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.db import get_session
from app.models.campaign import AssessmentCampaign, CampaignStatus
from app.models.interview import Interview
from app.models.member import Member, MemberTokenStatus
from app.models.node_state import NodeState, NodeStateStatus

logger = logging.getLogger(__name__)

router = APIRouter()


LEGACY_CAMPAIGN_NAME = "Diagnóstico Inicial"

_MEMBER_TO_NODE_STATE: dict[MemberTokenStatus, NodeStateStatus] = {
    MemberTokenStatus.PENDING: NodeStateStatus.INVITED,
    MemberTokenStatus.IN_PROGRESS: NodeStateStatus.IN_PROGRESS,
    MemberTokenStatus.COMPLETED: NodeStateStatus.COMPLETED,
    MemberTokenStatus.EXPIRED: NodeStateStatus.SKIPPED,
}


class PublicInterviewResponse(BaseModel):
    member_id: str
    name: str
    role_label: str
    token_status: MemberTokenStatus
    submitted_at: datetime | None = None
    schema_version: int = 1
    data: dict[str, Any] = Field(default_factory=dict)


class PublicInterviewSubmit(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


def _get_member_by_token(session: Session, token: str) -> Member:
    member = session.exec(select(Member).where(Member.interview_token == token)).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    if member.token_status == MemberTokenStatus.EXPIRED:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Interview token expired")
    return member


def _get_interview(session: Session, member_id: UUID) -> Interview | None:
    return session.exec(select(Interview).where(Interview.member_id == member_id)).first()


def _build_public_interview_response(
    member: Member,
    interview: Interview | None,
) -> PublicInterviewResponse:
    return PublicInterviewResponse(
        member_id=str(member.id),
        name=member.name,
        role_label=member.role_label,
        token_status=member.token_status,
        submitted_at=interview.submitted_at if interview else None,
        schema_version=interview.schema_version if interview else 1,
        data=interview.data if interview else {},
    )


# ────────────── Mirror helpers (Interview ↔ NodeState) ──────────────

def _get_or_create_legacy_campaign(
    session: Session,
    organization_id: UUID,
) -> AssessmentCampaign:
    campaign = session.exec(
        select(AssessmentCampaign).where(
            AssessmentCampaign.organization_id == organization_id,
            AssessmentCampaign.name == LEGACY_CAMPAIGN_NAME,
        )
    ).first()
    if campaign is not None:
        return campaign

    logger.warning(
        "Organización %s sin Campaign '%s'; creando on-the-fly (compat).",
        organization_id,
        LEGACY_CAMPAIGN_NAME,
    )
    campaign = AssessmentCampaign(
        organization_id=organization_id,
        created_by_user_id=None,
        name=LEGACY_CAMPAIGN_NAME,
        status=CampaignStatus.ACTIVE,
        started_at=datetime.now(timezone.utc),
    )
    session.add(campaign)
    session.flush()
    return campaign


def _mirror_interview_to_node_state(
    session: Session,
    member: Member,
    interview: Interview,
    *,
    is_submit: bool,
) -> None:
    """Upsert del NodeState espejo de un Interview.

    - is_submit=True  → status=COMPLETED, completed_at=interview.submitted_at.
    - is_submit=False → status=IN_PROGRESS (guardado de draft).

    La primera vez que el NodeState se crea, se usa id=interview.id para
    preservar UUIDs.
    """
    campaign = _get_or_create_legacy_campaign(session, member.organization_id)

    ns = session.exec(
        select(NodeState).where(
            NodeState.node_id == member.id,
            NodeState.campaign_id == campaign.id,
        )
    ).first()

    target_status = (
        NodeStateStatus.COMPLETED if is_submit else NodeStateStatus.IN_PROGRESS
    )

    if ns is None:
        ns = NodeState(
            id=interview.id,
            node_id=member.id,
            campaign_id=campaign.id,
            email_assigned=None,
            role_label=member.role_label,
            respondent_token=member.interview_token,
            status=target_status,
            interview_data=interview.data,
            invited_at=datetime.now(timezone.utc),
            completed_at=interview.submitted_at if is_submit else None,
        )
    else:
        ns.status = target_status
        ns.interview_data = interview.data
        ns.role_label = member.role_label
        if is_submit:
            ns.completed_at = interview.submitted_at
    session.add(ns)


# ─────────────────────────── Endpoints ──────────────────────────

@router.get("/entrevista/{token}", response_model=PublicInterviewResponse)
def get_public_interview(
    token: str,
    session: Session = Depends(get_session),
) -> PublicInterviewResponse:
    member = _get_member_by_token(session, token)
    interview = _get_interview(session, member.id)

    if member.token_status == MemberTokenStatus.PENDING:
        member.token_status = MemberTokenStatus.IN_PROGRESS
        session.add(member)
        session.commit()
        session.refresh(member)

    return _build_public_interview_response(member, interview)


@router.post("/entrevista/{token}/submit", response_model=PublicInterviewResponse)
def submit_public_interview(
    token: str,
    payload: PublicInterviewSubmit,
    session: Session = Depends(get_session),
) -> PublicInterviewResponse:
    member = _get_member_by_token(session, token)
    if member.token_status == MemberTokenStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Interview already submitted")

    interview = _get_interview(session, member.id)
    submitted_at = datetime.now(timezone.utc)

    if interview:
        interview.data = payload.data
        interview.submitted_at = submitted_at
    else:
        interview = Interview(
            member_id=member.id,
            organization_id=member.organization_id,
            group_id=member.group_id,
            data=payload.data,
            submitted_at=submitted_at,
            schema_version=1,
        )

    member.token_status = MemberTokenStatus.COMPLETED

    session.add(interview)
    session.add(member)
    session.flush()  # asegura interview.id y member fresh para el espejado

    # Mirror → NodeState (dentro de la misma transacción).
    _mirror_interview_to_node_state(session, member, interview, is_submit=True)

    session.commit()
    session.refresh(member)
    session.refresh(interview)

    return _build_public_interview_response(member, interview)


@router.post("/entrevista/{token}/draft", response_model=PublicInterviewResponse)
def save_public_interview_draft(
    token: str,
    payload: PublicInterviewSubmit,
    session: Session = Depends(get_session),
) -> PublicInterviewResponse:
    member = _get_member_by_token(session, token)
    if member.token_status == MemberTokenStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Interview already submitted")

    interview = _get_interview(session, member.id)

    if interview:
        interview.data = payload.data
    else:
        interview = Interview(
            member_id=member.id,
            organization_id=member.organization_id,
            group_id=member.group_id,
            data=payload.data,
            submitted_at=None,
            schema_version=1,
        )

    if member.token_status == MemberTokenStatus.PENDING:
        member.token_status = MemberTokenStatus.IN_PROGRESS

    session.add(interview)
    session.add(member)
    session.flush()

    _mirror_interview_to_node_state(session, member, interview, is_submit=False)

    session.commit()
    session.refresh(member)
    session.refresh(interview)

    return _build_public_interview_response(member, interview)
