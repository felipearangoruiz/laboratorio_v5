"""COMPATIBILITY LAYER — Sprint 1.4

Este router es legacy y expone una lectura agregada sobre `members` +
`interviews`. No realiza escrituras propias: las escrituras de Interview
viven en `interview_public.py`, que espeja sobre `node_states`.

El endpoint está marcado `deprecated=True`. Los consumidores nuevos
deben leer de /node-states con `campaign_id` filtrado.

Eliminar cuando:
  - El frontend lea la lista de entrevistas vía /node-states.
  - El motor de análisis no dependa de `interviews.data` directamente.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.core.dependencies import get_current_user
from app.db import get_session
from app.models.interview import Interview
from app.models.member import Member, MemberTokenStatus
from app.models.organization import Organization
from app.models.user import User, UserRole

router = APIRouter()


class OrganizationInterviewRead(BaseModel):
    member_id: UUID
    member_name: str
    role_label: str
    group_id: UUID | None = None
    token_status: MemberTokenStatus
    interview_id: UUID | None = None
    answers: dict[str, Any] = Field(default_factory=dict)
    submitted_at: datetime | None = None


def _can_access_org(user: User, org_id: UUID) -> bool:
    return user.role == UserRole.SUPERADMIN or user.organization_id == org_id


@router.get(
    "/organizations/{org_id}/interviews",
    response_model=list[OrganizationInterviewRead],
    deprecated=True,
)
def list_organization_interviews(
    org_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> list[OrganizationInterviewRead]:
    if not _can_access_org(current_user, org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    organization = session.get(Organization, org_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    rows = session.exec(
        select(Member, Interview)
        .outerjoin(Interview, Interview.member_id == Member.id)
        .where(Member.organization_id == org_id)
        .order_by(Member.created_at.desc())
    ).all()

    return [
        OrganizationInterviewRead(
            member_id=member.id,
            member_name=member.name,
            role_label=member.role_label,
            group_id=member.group_id,
            token_status=member.token_status,
            interview_id=interview.id if interview else None,
            answers=interview.data if interview else {},
            submitted_at=interview.submitted_at if interview else None,
        )
        for member, interview in rows
    ]
