"""Router para el flujo Free — Quick Assessment (diagnóstico rápido).

Endpoints públicos (no requieren auth):
- POST /quick-assessment                     → crear evaluación con respuestas del líder
- POST /quick-assessment/{id}/invite         → invitar miembros (3-5)
- GET  /quick-assessment/{id}/questions      → obtener preguntas para miembro
- POST /quick-assessment/{id}/respond/{token}→ respuesta de miembro
- GET  /quick-assessment/{id}/progress       → progreso en tiempo real
- GET  /quick-assessment/{id}/score          → obtener score radar

Endpoints autenticados:
- GET  /quick-assessment/{id}                → detalle (requiere auth, owner de la org)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, func, select

from app.db import get_session
from app.models.quick_assessment import (
    QuickAssessment,
    QuickAssessmentMember,
    QuickAssessmentMemberCreate,
    QuickAssessmentMemberRead,
    QuickAssessmentRead,
    QuickAssessmentStatus,
)
from app.questions_free import DIMENSIONS_FREE, LEADER_QUESTIONS, MEMBER_QUESTIONS

router = APIRouter()

MAX_FREE_MEMBERS = 5
MIN_RESPONSES_FOR_SCORE = 3


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CreateAssessmentRequest(BaseModel):
    organization_id: UUID
    leader_responses: dict[str, Any]


class InviteMembersRequest(BaseModel):
    members: list[QuickAssessmentMemberCreate]


class MemberResponseRequest(BaseModel):
    responses: dict[str, Any]


class ProgressResponse(BaseModel):
    total_invited: int
    total_completed: int
    threshold: int
    ready: bool


class ScoreResponse(BaseModel):
    assessment_id: UUID
    scores: dict[str, float]
    member_count: int
    status: QuickAssessmentStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_assessment_or_404(session: Session, assessment_id: UUID) -> QuickAssessment:
    assessment = session.get(QuickAssessment, assessment_id)
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )
    return assessment


def _compute_scores(
    leader_responses: dict[str, Any],
    member_responses: list[dict[str, Any]],
) -> dict[str, float]:
    """Calcula score promedio por dimensión combinando respuestas del líder y miembros."""
    dimension_values: dict[str, list[float]] = {d: [] for d in DIMENSIONS_FREE}

    # Procesar respuestas del líder (preguntas Likert)
    for q in LEADER_QUESTIONS:
        if q["tipo"] != "likert":
            continue
        val = leader_responses.get(q["id"])
        if val is not None and q["dimension"] in dimension_values:
            try:
                dimension_values[q["dimension"]].append(float(val))
            except (ValueError, TypeError):
                pass

    # Procesar respuestas de miembros (preguntas Likert)
    for member_resp in member_responses:
        for q in MEMBER_QUESTIONS:
            if q["tipo"] != "likert":
                continue
            val = member_resp.get(q["id"])
            if val is not None and q["dimension"] in dimension_values:
                try:
                    dimension_values[q["dimension"]].append(float(val))
                except (ValueError, TypeError):
                    pass

    scores: dict[str, float] = {}
    for dim, values in dimension_values.items():
        if values:
            scores[dim] = round(sum(values) / len(values), 2)
        else:
            scores[dim] = 0.0

    return scores


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/quick-assessment", response_model=QuickAssessmentRead, status_code=201)
def create_assessment(
    payload: CreateAssessmentRequest,
    session: Session = Depends(get_session),
) -> QuickAssessment:
    """Crea evaluación rápida con las respuestas del líder."""
    assessment = QuickAssessment(
        organization_id=payload.organization_id,
        leader_responses=payload.leader_responses,
        status=QuickAssessmentStatus.WAITING,
    )
    session.add(assessment)
    session.commit()
    session.refresh(assessment)
    return assessment


@router.post(
    "/quick-assessment/{assessment_id}/invite",
    response_model=list[QuickAssessmentMemberRead],
    status_code=201,
)
def invite_members(
    assessment_id: UUID,
    payload: InviteMembersRequest,
    session: Session = Depends(get_session),
) -> list[QuickAssessmentMember]:
    """Invita miembros al diagnóstico rápido (máximo 5 en total)."""
    assessment = _get_assessment_or_404(session, assessment_id)

    existing_count = session.exec(
        select(func.count())
        .select_from(QuickAssessmentMember)
        .where(QuickAssessmentMember.assessment_id == assessment.id)
    ).one()

    if existing_count + len(payload.members) > MAX_FREE_MEMBERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot exceed {MAX_FREE_MEMBERS} members in free plan. "
            f"Currently {existing_count}, trying to add {len(payload.members)}.",
        )

    if len(payload.members) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 1 member is required.",
        )

    # Verificar emails duplicados dentro del assessment
    existing_emails = set(
        session.exec(
            select(QuickAssessmentMember.email).where(
                QuickAssessmentMember.assessment_id == assessment.id
            )
        ).all()
    )
    new_emails = [m.email for m in payload.members]
    duplicates = existing_emails & set(new_emails)
    if duplicates:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Emails already invited: {', '.join(duplicates)}",
        )

    created: list[QuickAssessmentMember] = []
    for member_data in payload.members:
        member = QuickAssessmentMember(
            assessment_id=assessment.id,
            name=member_data.name,
            role_label=member_data.role_label,
            email=member_data.email,
        )
        session.add(member)
        created.append(member)

    assessment.member_count = existing_count + len(payload.members)
    session.add(assessment)
    session.commit()

    for m in created:
        session.refresh(m)

    return created


@router.get("/quick-assessment/{assessment_id}/questions")
def get_member_questions(assessment_id: UUID) -> list[dict]:
    """Devuelve las preguntas que debe responder un miembro invitado."""
    return MEMBER_QUESTIONS


@router.post(
    "/quick-assessment/{assessment_id}/respond/{token}",
    response_model=QuickAssessmentMemberRead,
)
def submit_member_response(
    assessment_id: UUID,
    token: str,
    payload: MemberResponseRequest,
    session: Session = Depends(get_session),
) -> QuickAssessmentMember:
    """Registra la respuesta de un miembro invitado."""
    assessment = _get_assessment_or_404(session, assessment_id)

    member = session.exec(
        select(QuickAssessmentMember).where(
            QuickAssessmentMember.assessment_id == assessment.id,
            QuickAssessmentMember.token == token,
        )
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found for this assessment",
        )

    if member.completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Response already submitted",
        )

    member.responses = payload.responses
    member.completed = True
    session.add(member)

    # Contar respuestas completadas
    completed_count = session.exec(
        select(func.count())
        .select_from(QuickAssessmentMember)
        .where(
            QuickAssessmentMember.assessment_id == assessment.id,
            QuickAssessmentMember.completed == True,  # noqa: E712
        )
    ).one()

    # Si alcanza el umbral, generar scores automáticamente
    if completed_count >= MIN_RESPONSES_FOR_SCORE and assessment.status == QuickAssessmentStatus.WAITING:
        all_members = session.exec(
            select(QuickAssessmentMember).where(
                QuickAssessmentMember.assessment_id == assessment.id,
                QuickAssessmentMember.completed == True,  # noqa: E712
            )
        ).all()

        member_responses = [m.responses for m in all_members]
        scores = _compute_scores(assessment.leader_responses, member_responses)

        assessment.scores = scores
        assessment.status = QuickAssessmentStatus.READY
        session.add(assessment)

    session.commit()
    session.refresh(member)
    return member


@router.get("/quick-assessment/{assessment_id}/progress", response_model=ProgressResponse)
def get_progress(
    assessment_id: UUID,
    session: Session = Depends(get_session),
) -> ProgressResponse:
    """Progreso de respuestas en tiempo real."""
    assessment = _get_assessment_or_404(session, assessment_id)

    completed_count = session.exec(
        select(func.count())
        .select_from(QuickAssessmentMember)
        .where(
            QuickAssessmentMember.assessment_id == assessment.id,
            QuickAssessmentMember.completed == True,  # noqa: E712
        )
    ).one()

    return ProgressResponse(
        total_invited=assessment.member_count,
        total_completed=completed_count,
        threshold=MIN_RESPONSES_FOR_SCORE,
        ready=completed_count >= MIN_RESPONSES_FOR_SCORE,
    )


@router.get("/quick-assessment/{assessment_id}/score", response_model=ScoreResponse)
def get_score(
    assessment_id: UUID,
    session: Session = Depends(get_session),
) -> ScoreResponse:
    """Obtiene el score radar. Si ya está calculado lo devuelve; si no, lo calcula si hay suficientes respuestas."""
    assessment = _get_assessment_or_404(session, assessment_id)

    # Si el score ya fue calculado, devolverlo
    if assessment.status in (QuickAssessmentStatus.READY, QuickAssessmentStatus.COMPLETED):
        return ScoreResponse(
            assessment_id=assessment.id,
            scores=assessment.scores,
            member_count=assessment.member_count,
            status=assessment.status,
        )

    # Intentar calcular si hay suficientes respuestas
    completed_members = session.exec(
        select(QuickAssessmentMember).where(
            QuickAssessmentMember.assessment_id == assessment.id,
            QuickAssessmentMember.completed == True,  # noqa: E712
        )
    ).all()

    if len(completed_members) < MIN_RESPONSES_FOR_SCORE:
        raise HTTPException(
            status_code=status.HTTP_425_TOO_EARLY,
            detail=f"Need at least {MIN_RESPONSES_FOR_SCORE} responses. "
            f"Currently {len(completed_members)}.",
        )

    member_responses = [m.responses for m in completed_members]
    scores = _compute_scores(assessment.leader_responses, member_responses)

    assessment.scores = scores
    assessment.status = QuickAssessmentStatus.READY
    session.add(assessment)
    session.commit()
    session.refresh(assessment)

    return ScoreResponse(
        assessment_id=assessment.id,
        scores=assessment.scores,
        member_count=assessment.member_count,
        status=assessment.status,
    )


@router.get("/quick-assessment/{assessment_id}/leader-questions")
def get_leader_questions(assessment_id: UUID) -> list[dict]:
    """Devuelve las preguntas de la encuesta del líder."""
    return LEADER_QUESTIONS
