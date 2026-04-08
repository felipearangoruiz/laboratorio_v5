from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.dependencies import get_current_user
from app.db import get_session
from app.models.group import Group
from app.models.member import Member
from app.models.organization import (
    Organization,
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
)
from app.models.user import User, UserRole

router = APIRouter()


class OrgStats(BaseModel):
    total_members: int
    total_groups: int
    completed_interviews: int
    pending_interviews: int


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> OrganizationRead:
    if current_user.role == UserRole.ADMIN:
        if current_user.organization_id is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )

        if payload.admin_id is not None and payload.admin_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )

        organization = Organization(
            **payload.model_dump(exclude={"admin_id"}),
            admin_id=current_user.id,
        )
        session.add(organization)
        session.flush()

        current_user.organization_id = organization.id
        session.add(current_user)
        session.commit()
        session.refresh(organization)
        return OrganizationRead.model_validate(organization)

    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    organization = Organization(**payload.model_dump())
    session.add(organization)
    session.commit()
    session.refresh(organization)
    return OrganizationRead.model_validate(organization)


@router.get("", response_model=list[OrganizationRead])
def list_organizations(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> list[OrganizationRead]:
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    organizations = session.exec(select(Organization)).all()
    return [OrganizationRead.model_validate(org) for org in organizations]


@router.get("/{organization_id}", response_model=OrganizationRead)
def get_organization(
    organization_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> OrganizationRead:
    organization = session.get(Organization, organization_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    if (
        current_user.role != UserRole.SUPERADMIN
        and current_user.organization_id != organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    return OrganizationRead.model_validate(organization)


@router.patch("/{organization_id}", response_model=OrganizationRead)
def update_organization(
    organization_id: UUID,
    payload: OrganizationUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> OrganizationRead:
    organization = session.get(Organization, organization_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    if (
        current_user.role != UserRole.SUPERADMIN
        and current_user.organization_id != organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(organization, field, value)

    session.add(organization)
    session.commit()
    session.refresh(organization)
    return OrganizationRead.model_validate(organization)


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
    organization_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> None:
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    organization = session.get(Organization, organization_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    session.delete(organization)
    session.commit()


@router.get("/{organization_id}/stats", response_model=OrgStats)
def get_organization_stats(
    organization_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> OrgStats:
    organization = session.get(Organization, organization_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    if (
        current_user.role != UserRole.SUPERADMIN
        and current_user.organization_id != organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    total_members = session.exec(
        select(func.count(Member.id)).where(Member.organization_id == organization_id)
    ).one()
    total_groups = session.exec(
        select(func.count(Group.id)).where(Group.organization_id == organization_id)
    ).one()
    completed_interviews = session.exec(
        select(func.count(Member.id)).where(
            Member.organization_id == organization_id,
            Member.token_status == "completed",
        )
    ).one()
    pending_interviews = session.exec(
        select(func.count(Member.id)).where(
            Member.organization_id == organization_id,
            Member.token_status == "pending",
        )
    ).one()

    return OrgStats(
        total_members=total_members,
        total_groups=total_groups,
        completed_interviews=completed_interviews,
        pending_interviews=pending_interviews,
    )
