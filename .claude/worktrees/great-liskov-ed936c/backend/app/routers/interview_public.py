from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.db import get_session
from app.models.interview import Interview
from app.models.member import Member, MemberTokenStatus

router = APIRouter()


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
    session.commit()
    session.refresh(member)
    session.refresh(interview)

    return _build_public_interview_response(member, interview)
