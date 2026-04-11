from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.dependencies import get_current_user
from app.db import get_session
from app.models.group import Group
from app.models.job import JobStatus
from app.models.member import Member
from app.models.organization import (
    Organization,
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
)
from app.models.processing import ProcessingResult
from app.models.user import User, UserRole

router = APIRouter()


class OrgStats(BaseModel):
    total_members: int
    total_groups: int
    completed_interviews: int
    pending_interviews: int


class DashboardPendingInterview(BaseModel):
    member_id: UUID
    member_name: str
    role_label: str
    group_id: UUID | None = None
    token_status: str


class DashboardLatestResult(BaseModel):
    id: UUID
    type: str
    created_at: str


class DashboardLatestJob(BaseModel):
    id: UUID
    status: str
    error: str | None = None
    created_at: str
    updated_at: str


class DashboardStrategicContext(BaseModel):
    strategic_objectives: str
    strategic_concerns: str
    key_questions: str
    additional_context: str
    is_complete: bool


class OrganizationDashboard(BaseModel):
    organization: OrganizationRead
    total_members: int
    total_groups: int
    completed_interviews: int
    in_progress_interviews: int
    pending_interviews: int
    completion_pct: int
    pending_actions: list[str]
    pending_interviews_list: list[DashboardPendingInterview]
    can_generate_diagnosis: bool
    strategic_context: DashboardStrategicContext
    latest_result: DashboardLatestResult | None = None
    latest_job: DashboardLatestJob | None = None


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
        total_members=int(total_members),
        total_groups=int(total_groups),
        completed_interviews=int(completed_interviews),
        pending_interviews=int(pending_interviews),
    )


@router.get("/{organization_id}/dashboard", response_model=OrganizationDashboard)
def get_organization_dashboard(
    organization_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> OrganizationDashboard:
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

    total_members = int(
        session.exec(select(func.count(Member.id)).where(Member.organization_id == organization_id)).one()
    )
    total_groups = int(
        session.exec(select(func.count(Group.id)).where(Group.organization_id == organization_id)).one()
    )
    completed_interviews = int(
        session.exec(
            select(func.count(Member.id)).where(
                Member.organization_id == organization_id,
                Member.token_status == "completed",
            )
        ).one()
    )
    pending_interviews = int(
        session.exec(
            select(func.count(Member.id)).where(
                Member.organization_id == organization_id,
                Member.token_status == "pending",
            )
        ).one()
    )
    in_progress_interviews = int(
        session.exec(
            select(func.count(Member.id)).where(
                Member.organization_id == organization_id,
                Member.token_status == "in_progress",
            )
        ).one()
    )

    pending_members = session.exec(
        select(Member)
        .where(
            Member.organization_id == organization_id,
            Member.token_status != "completed",
        )
        .order_by(Member.created_at.desc())
        .limit(5)
    ).all()

    latest_result = session.exec(
        select(ProcessingResult)
        .where(ProcessingResult.organization_id == organization_id)
        .order_by(ProcessingResult.created_at.desc())
    ).first()
    latest_job = session.exec(
        select(JobStatus)
        .where(JobStatus.organization_id == organization_id)
        .order_by(JobStatus.created_at.desc())
    ).first()

    pending_actions: list[str] = []
    if total_groups == 0:
        pending_actions.append("Crea la estructura base de la organización para ordenar el levantamiento.")
    if total_members == 0:
        pending_actions.append("Agrega miembros para poder iniciar entrevistas.")
    if total_members > 0 and completed_interviews == 0:
        pending_actions.append("Comparte y completa al menos una entrevista para empezar a generar señal.")
    if total_members > 0 and completed_interviews < total_members:
        pending_actions.append("Aún faltan entrevistas por completar para mejorar la lectura del caso.")
    if not any(
        [
            organization.strategic_objectives.strip(),
            organization.strategic_concerns.strip(),
            organization.key_questions.strip(),
            organization.additional_context.strip(),
        ]
    ):
        pending_actions.append(
            "Captura el contexto estratégico del caso para orientar mejor el diagnóstico."
        )
    if latest_result is None:
        pending_actions.append("Todavía no hay resultados generados para esta organización.")

    completion_pct = round((completed_interviews / total_members) * 100) if total_members else 0
    can_generate_diagnosis = completed_interviews > 0

    return OrganizationDashboard(
        organization=OrganizationRead.model_validate(organization),
        total_members=total_members,
        total_groups=total_groups,
        completed_interviews=completed_interviews,
        in_progress_interviews=in_progress_interviews,
        pending_interviews=pending_interviews,
        completion_pct=completion_pct,
        pending_actions=pending_actions,
        pending_interviews_list=[
            DashboardPendingInterview(
                member_id=member.id,
                member_name=member.name,
                role_label=member.role_label,
                group_id=member.group_id,
                token_status=member.token_status.value,
            )
            for member in pending_members
        ],
        can_generate_diagnosis=can_generate_diagnosis,
        strategic_context=DashboardStrategicContext(
            strategic_objectives=organization.strategic_objectives,
            strategic_concerns=organization.strategic_concerns,
            key_questions=organization.key_questions,
            additional_context=organization.additional_context,
            is_complete=any(
                [
                    organization.strategic_objectives.strip(),
                    organization.strategic_concerns.strip(),
                    organization.key_questions.strip(),
                    organization.additional_context.strip(),
                ]
            ),
        ),
        latest_result=(
            DashboardLatestResult(
                id=latest_result.id,
                type=latest_result.type.value,
                created_at=latest_result.created_at.isoformat(),
            )
            if latest_result
            else None
        ),
        latest_job=(
            DashboardLatestJob(
                id=latest_job.id,
                status=latest_job.status.value,
                error=latest_job.error,
                created_at=latest_job.created_at.isoformat(),
                updated_at=latest_job.updated_at.isoformat(),
            )
            if latest_job
            else None
        ),
    )
