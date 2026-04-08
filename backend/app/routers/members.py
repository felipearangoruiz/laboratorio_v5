from __future__ import annotations

import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.dependencies import get_current_user
from app.db import get_session
from app.models.group import Group
from app.models.member import Member, MemberRead, MemberTokenStatus
from app.models.user import User, UserRole

router = APIRouter()


class MemberCreate(BaseModel):
    organization_id: UUID
    name: str
    role_label: str = ""
    group_id: UUID | None = None


class MemberUpdate(BaseModel):
    name: str | None = None
    role_label: str | None = None
    group_id: UUID | None = None
    token_status: MemberTokenStatus | None = None


class MemberMoveGroup(BaseModel):
    group_id: UUID | None


def _can_access_org(user: User, organization_id: UUID) -> bool:
    return user.role == UserRole.SUPERADMIN or user.organization_id == organization_id


def _ensure_member_access(member: Member, user: User) -> None:
    if not _can_access_org(user, member.organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")


def _validate_group_assignment(
    session: Session,
    organization_id: UUID,
    group_id: UUID | None,
) -> None:
    if group_id is None:
        return

    group = session.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    if group.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group must belong to same organization",
        )


def _generate_unique_token(session: Session) -> str:
    for _ in range(10):
        token = secrets.token_urlsafe(24)
        exists = session.exec(select(Member).where(Member.interview_token == token)).first()
        if not exists:
            return token
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not generate token")


@router.post("/members", response_model=MemberRead, status_code=status.HTTP_201_CREATED)
def create_member(
    payload: MemberCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> MemberRead:
    if not _can_access_org(current_user, payload.organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    _validate_group_assignment(session, payload.organization_id, payload.group_id)

    member = Member(
        organization_id=payload.organization_id,
        group_id=payload.group_id,
        name=payload.name,
        role_label=payload.role_label,
        interview_token=_generate_unique_token(session),
        token_status=MemberTokenStatus.PENDING,
    )
    session.add(member)
    session.commit()
    session.refresh(member)
    return MemberRead.model_validate(member)


@router.get("/members/{member_id}", response_model=MemberRead)
def get_member(
    member_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> MemberRead:
    member = session.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    _ensure_member_access(member, current_user)
    return MemberRead.model_validate(member)


@router.patch("/members/{member_id}", response_model=MemberRead)
def update_member(
    member_id: UUID,
    payload: MemberUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> MemberRead:
    member = session.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    _ensure_member_access(member, current_user)

    update_data = payload.model_dump(exclude_unset=True)
    if "group_id" in update_data:
        _validate_group_assignment(session, member.organization_id, update_data["group_id"])

    for field, value in update_data.items():
        setattr(member, field, value)

    session.add(member)
    session.commit()
    session.refresh(member)
    return MemberRead.model_validate(member)


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    member_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
):
    member = session.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    _ensure_member_access(member, current_user)

    session.delete(member)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/organizations/{org_id}/members", response_model=list[MemberRead])
def list_members_by_organization(
    org_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> list[MemberRead]:
    if not _can_access_org(current_user, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    members = session.exec(select(Member).where(Member.organization_id == org_id)).all()
    return [MemberRead.model_validate(member) for member in members]


@router.get("/groups/{group_id}/members", response_model=list[MemberRead])
def list_members_by_group(
    group_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> list[MemberRead]:
    group = session.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    if not _can_access_org(current_user, group.organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    members = session.exec(select(Member).where(Member.group_id == group_id)).all()
    return [MemberRead.model_validate(member) for member in members]


@router.patch("/members/{member_id}/group", response_model=MemberRead)
def move_member_group(
    member_id: UUID,
    payload: MemberMoveGroup,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> MemberRead:
    member = session.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    _ensure_member_access(member, current_user)
    _validate_group_assignment(session, member.organization_id, payload.group_id)

    member.group_id = payload.group_id
    session.add(member)
    session.commit()
    session.refresh(member)
    return MemberRead.model_validate(member)
