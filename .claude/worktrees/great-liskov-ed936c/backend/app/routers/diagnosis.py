"""Endpoints for diagnosis generation and retrieval."""
from __future__ import annotations

import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.dependencies import get_current_user
from app.db import get_session
from app.models.diagnosis import DiagnosisResult, DiagnosisResultRead
from app.models.group import Group
from app.models.member import Member, MemberTokenStatus
from app.models.user import User, UserRole
from app.services.analysis import run_diagnosis_pipeline
from sqlalchemy import func as sa_func

router = APIRouter()

THRESHOLD_PERCENT = 0.40
THRESHOLD_MIN = 5


def _can_access(user: User, org_id: UUID) -> bool:
    return user.role == UserRole.SUPERADMIN or user.organization_id == org_id


@router.post("/organizations/{org_id}/diagnosis/generate", response_model=DiagnosisResultRead)
async def generate_diagnosis(
    org_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> DiagnosisResultRead:
    if not _can_access(current_user, org_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    # Verify threshold
    total_nodes = session.exec(
        select(sa_func.count(Group.id)).where(Group.organization_id == org_id)
    ).one()

    completed = session.exec(
        select(sa_func.count(Member.id)).where(
            Member.organization_id == org_id,
            Member.token_status == MemberTokenStatus.COMPLETED,
        )
    ).one()

    nodes_with_interview = session.exec(
        select(sa_func.count(sa_func.distinct(Member.group_id))).where(
            Member.organization_id == org_id,
            Member.token_status == MemberTokenStatus.COMPLETED,
            Member.group_id.is_not(None),
        )
    ).one()

    if total_nodes > 0:
        pct = nodes_with_interview / total_nodes
    else:
        pct = 0

    if completed < THRESHOLD_MIN or pct < THRESHOLD_PERCENT:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Umbral no alcanzado: {completed} entrevistas completadas "
                f"(mín {THRESHOLD_MIN}), {nodes_with_interview}/{total_nodes} nodos "
                f"({round(pct * 100)}%, mín {round(THRESHOLD_PERCENT * 100)}%)"
            ),
        )

    # Create a running result
    result = DiagnosisResult(organization_id=org_id, status="running")
    session.add(result)
    session.commit()
    session.refresh(result)

    try:
        pipeline_result = await run_diagnosis_pipeline(session, org_id)

        result.scores = pipeline_result["scores"]
        result.narrative = pipeline_result["narrative"]
        result.network_metrics = pipeline_result["network_metrics"]
        result.status = "completed"
    except Exception as e:
        result.status = "failed"
        result.error = str(e)

    session.add(result)
    session.commit()
    session.refresh(result)

    return DiagnosisResultRead.model_validate(result)


@router.get("/organizations/{org_id}/diagnosis/latest", response_model=DiagnosisResultRead | None)
def get_latest_diagnosis(
    org_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> DiagnosisResultRead | None:
    if not _can_access(current_user, org_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    result = session.exec(
        select(DiagnosisResult)
        .where(DiagnosisResult.organization_id == org_id)
        .order_by(DiagnosisResult.created_at.desc())
    ).first()

    if not result:
        return None

    return DiagnosisResultRead.model_validate(result)
