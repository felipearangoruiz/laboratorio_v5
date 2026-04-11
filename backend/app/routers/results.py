from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.core.dependencies import get_current_user
from app.db import get_session
from app.models.interview import Interview
from app.models.job import JobState, JobStatus
from app.models.member import Member
from app.models.organization import Organization
from app.models.processing import ProcessingResult, ProcessingType
from app.models.user import User, UserRole

router = APIRouter()


class ProcessingResultResponse(BaseModel):
    id: UUID
    organization_id: UUID
    group_id: UUID | None = None
    type: str
    result: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class TriggerProcessingResponse(BaseModel):
    job_id: UUID
    status: str
    result_id: UUID


class LatestJobResponse(BaseModel):
    id: UUID
    status: str
    error: str | None = None
    created_at: datetime
    updated_at: datetime


def _can_access_org(user: User, organization_id: UUID) -> bool:
    return user.role == UserRole.SUPERADMIN or user.organization_id == organization_id


def _get_org_or_404(session: Session, org_id: UUID) -> Organization:
    organization = session.get(Organization, org_id)
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return organization


def _extract_strings(interviews: list[Interview]) -> list[str]:
    chunks: list[str] = []
    for interview in interviews:
        for value in (interview.data or {}).values():
            if isinstance(value, str) and value.strip():
                chunks.append(value.strip())
    return chunks


def _count_mentions(texts: list[str], keywords: list[str]) -> int:
    total = 0
    lowered_texts = [text.lower() for text in texts]
    for text in lowered_texts:
        for keyword in keywords:
            if keyword in text:
                total += 1
    return total


def _build_processing_result(organization: Organization, interviews: list[Interview]) -> dict[str, Any]:
    texts = _extract_strings(interviews)
    total_interviews = len(interviews)
    total_answers = sum(len(interview.data or {}) for interview in interviews)

    decision_mentions = _count_mentions(
        texts,
        ["decisión", "decisiones", "aprobación", "aprueban", "aprueba", "permiso"],
    )
    friction_mentions = _count_mentions(
        texts,
        ["espera", "demora", "bloqueo", "fricción", "cuello", "retraso", "traba"],
    )
    rule_mentions = _count_mentions(
        texts,
        ["regla", "proceso", "formal", "informal", "procedimiento"],
    )
    incentive_mentions = _count_mentions(
        texts,
        ["incentivo", "reconoce", "recompensa", "conviene", "métrica"],
    )

    coverage_score = min(100, total_interviews * 20)
    friction_score = min(100, 30 + friction_mentions * 5)
    governance_score = min(100, 35 + decision_mentions * 5)
    rule_score = min(100, 35 + rule_mentions * 4)
    incentive_score = min(100, 35 + incentive_mentions * 4)
    global_score = round((coverage_score + friction_score + governance_score + rule_score + incentive_score) / 5)

    hallazgos = [
        f"Se procesaron {total_interviews} entrevistas con {total_answers} respuestas consolidadas.",
        f"Las menciones a fricción operativa aparecen {friction_mentions} veces en las respuestas capturadas.",
        f"Las referencias a toma de decisión y aprobaciones aparecen {decision_mentions} veces, lo que sugiere focos de gobernanza a revisar.",
    ]

    riesgos = []
    if friction_mentions > 0:
        riesgos.append("Hay señales de fricción operativa y dependencia entre áreas.")
    if decision_mentions > 0:
        riesgos.append("La toma de decisiones parece concentrarse o depender de aprobaciones no siempre explícitas.")
    if rule_mentions > 0:
        riesgos.append("Existen menciones a brechas entre reglas formales y práctica cotidiana.")
    if not riesgos:
        riesgos.append("La muestra todavía es pequeña; el principal riesgo es sobrerreaccionar con evidencia limitada.")

    recomendaciones = [
        "Completar más entrevistas para aumentar cobertura y reducir sesgo de muestra.",
        "Revisar procesos con mayor mención de espera, bloqueo o dependencia de aprobación.",
        "Contrastar reglas formales con prácticas recurrentes reportadas por los entrevistados.",
    ]

    return {
        "resumen_ejecutivo": (
            f"Diagnóstico básico para {organization.name}. La organización cuenta con {total_interviews} entrevistas "
            "procesadas y una lectura inicial centrada en gobernanza, fricción operativa y reglas reales de trabajo."
        ),
        "lectura_general": (
            "Este resultado es una primera consolidación estructurada del material capturado. "
            "No reemplaza una lectura cualitativa profunda, pero sí permite detectar patrones repetidos y orientar el siguiente ciclo del caso."
        ),
        "hallazgos_clave": hallazgos,
        "riesgos_principales": riesgos,
        "recomendaciones": recomendaciones,
        "cobertura": {
            "entrevistas_procesadas": total_interviews,
            "respuestas_consolidadas": total_answers,
        },
        "scores": {
            "cobertura": coverage_score,
            "friccion_operativa": friction_score,
            "gobernanza": governance_score,
            "claridad_reglas": rule_score,
            "incentivos": incentive_score,
            "salud_global": global_score,
        },
    }


@router.get("/organizations/{org_id}/results", response_model=list[ProcessingResultResponse])
def list_processing_results(
    org_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> list[ProcessingResultResponse]:
    if not _can_access_org(current_user, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    _get_org_or_404(session, org_id)

    rows = session.exec(
        select(ProcessingResult)
        .where(ProcessingResult.organization_id == org_id)
        .order_by(ProcessingResult.created_at.desc())
    ).all()

    return [
        ProcessingResultResponse(
            id=row.id,
            organization_id=row.organization_id,
            group_id=row.group_id,
            type=row.type.value,
            result=row.result,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.get("/organizations/{org_id}/results/latest", response_model=ProcessingResultResponse | None)
def get_latest_processing_result(
    org_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> ProcessingResultResponse | None:
    if not _can_access_org(current_user, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    _get_org_or_404(session, org_id)

    row = session.exec(
        select(ProcessingResult)
        .where(ProcessingResult.organization_id == org_id)
        .order_by(ProcessingResult.created_at.desc())
    ).first()

    if row is None:
        return None

    return ProcessingResultResponse(
        id=row.id,
        organization_id=row.organization_id,
        group_id=row.group_id,
        type=row.type.value,
        result=row.result,
        created_at=row.created_at,
    )


@router.get("/organizations/{org_id}/results/status/latest", response_model=LatestJobResponse | None)
def get_latest_processing_job(
    org_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> LatestJobResponse | None:
    if not _can_access_org(current_user, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    _get_org_or_404(session, org_id)

    job = session.exec(
        select(JobStatus)
        .where(JobStatus.organization_id == org_id)
        .order_by(JobStatus.created_at.desc())
    ).first()

    if job is None:
        return None

    return LatestJobResponse(
        id=job.id,
        status=job.status.value,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.post(
    "/organizations/{org_id}/results/trigger",
    response_model=TriggerProcessingResponse,
    status_code=status.HTTP_201_CREATED,
)
def trigger_processing_result(
    org_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> TriggerProcessingResponse:
    if not _can_access_org(current_user, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    organization = _get_org_or_404(session, org_id)

    interviews = session.exec(
        select(Interview)
        .join(Member, Member.id == Interview.member_id)
        .where(
            Interview.organization_id == org_id,
            Member.token_status == "completed",
            Interview.submitted_at.is_not(None),
        )
        .order_by(Interview.submitted_at.desc())
    ).all()

    if not interviews:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay entrevistas completadas para generar diagnóstico",
        )

    now = datetime.now(timezone.utc)
    job = JobStatus(
        organization_id=org_id,
        status=JobState.PENDING,
        error=None,
        created_at=now,
        updated_at=now,
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    try:
        job.status = JobState.RUNNING
        job.updated_at = datetime.now(timezone.utc)
        session.add(job)
        session.commit()
        session.refresh(job)

        result_payload = _build_processing_result(organization, interviews)
        result = ProcessingResult(
            organization_id=org_id,
            group_id=None,
            type=ProcessingType.CIEGO,
            result=result_payload,
        )
        session.add(result)

        job.status = JobState.COMPLETED
        job.updated_at = datetime.now(timezone.utc)
        session.add(job)

        session.commit()
        session.refresh(job)
        session.refresh(result)
    except Exception as exc:
        job.status = JobState.FAILED
        job.error = str(exc)
        job.updated_at = datetime.now(timezone.utc)
        session.add(job)
        session.commit()
        raise

    return TriggerProcessingResponse(
        job_id=job.id,
        status=job.status.value,
        result_id=result.id,
    )
