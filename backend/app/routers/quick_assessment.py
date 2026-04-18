from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db import get_session
from app.models.quick_assessment import (
    DimensionScoreRead,
    InviteMembersRequest,
    MemberRespondRequest,
    QuickAssessment,
    QuickAssessmentCreate,
    QuickAssessmentMember,
    QuickAssessmentRead,
    QuickAssessmentScoreRead,
)
from app.questions_instrument_v2 import (
    ADAPTIVE_QUESTIONS,
    FREE_DIMENSIONS_V2 as FREE_DIMENSIONS,
    FREE_EMPLOYEE_QUESTIONS,
    FREE_MANAGER_QUESTIONS as FREE_QUESTIONS,
    FREE_MANAGER_QUESTION_IDS,
    select_adaptive_questions,
)


def _all_valid_ids() -> set[str]:
    """IDs aceptados en responses: preguntas base + capas + adaptativas + sus capas."""
    ids: set[str] = set()
    for q in FREE_QUESTIONS + FREE_EMPLOYEE_QUESTIONS + ADAPTIVE_QUESTIONS:
        ids.add(q["id"])
        for layer in q.get("layers", []):
            lid = layer.get("id")
            if lid:
                ids.add(lid)
    return ids


VALID_RESPONSE_IDS = _all_valid_ids()

router = APIRouter()


def _compute_scores(
    leader_responses: dict,
    member_responses_list: list[dict],
) -> dict:
    """Compute average score per dimension combining leader + member responses.

    Instrumento v2 completo: cruza preguntas del gerente (G*), empleado (E*) y
    adaptativas (A*), así como las capas numéricas (numeric_select, scale_1_5).
    Los tipos categóricos (multi_select, text) no aportan al score cuantitativo
    pero sí se capturan para el análisis narrativo.

    Normalización: índice de opción (0-based) → escala 1-5 vía
    (idx / (num_options - 1)) * 4 + 1.
    """
    dimension_scores: dict[str, list[float]] = {dim: [] for dim in FREE_DIMENSIONS}

    # Construir metadata de todas las preguntas y capas del instrumento free
    # q_meta: id → (dimension, num_options, type)
    all_questions = FREE_QUESTIONS + FREE_EMPLOYEE_QUESTIONS + ADAPTIVE_QUESTIONS
    q_meta: dict[str, tuple[str, int, str]] = {}
    for q in all_questions:
        base_type = q["base"].get("type", "")
        num_opts = len(q["base"].get("options", [])) or 5
        q_meta[q["id"]] = (q["dimension"], num_opts, base_type)
        for layer in q.get("layers", []):
            lid = layer.get("id")
            if lid:
                q_meta[lid] = (
                    q["dimension"],
                    len(layer.get("options", [])) or 5,
                    layer.get("type", ""),
                )

    # Tipos que aportan score numérico (índice de opción → escala 1-5)
    SCORABLE_TYPES = {"single_select", "numeric_select", "scale_1_5"}

    def _add_responses(responses: dict) -> None:
        for qid, val in responses.items():
            meta = q_meta.get(qid)
            if not meta:
                continue
            dim, num_opts, qtype = meta
            if qtype not in SCORABLE_TYPES:
                continue
            if isinstance(val, (int, float)):
                normalised = (float(val) / max(num_opts - 1, 1)) * 4 + 1
                dimension_scores[dim].append(normalised)

    _add_responses(leader_responses)
    for resp in member_responses_list:
        _add_responses(resp)

    result = {}
    for dim, values in dimension_scores.items():
        if values:
            result[dim] = round(sum(values) / len(values), 2)
        else:
            result[dim] = 0.0

    return result


# ── Public endpoints (no auth) — MUST come before /{assessment_id} routes ──

@router.get("/leader-questions")
def get_leader_questions() -> dict:
    """Public endpoint — no auth. Devuelve las 13 preguntas del gerente del
    instrumento v2 completo (flujo free). Se usa en el onboarding."""
    return {
        "questions": FREE_QUESTIONS,
        "dimensions": FREE_DIMENSIONS,
    }


@router.get("/interview/{token}")
def get_member_interview(
    token: str,
    session: Session = Depends(get_session),
) -> dict:
    """Public endpoint — no auth. Fetch interview state for a member by token.

    Devuelve las 10 preguntas base del empleado + hasta 3 preguntas adaptativas
    seleccionadas según las hipótesis activas detectadas en las respuestas
    del gerente (instrumento v2 completo — flujo free).
    """
    member = session.exec(
        select(QuickAssessmentMember).where(QuickAssessmentMember.token == token)
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Invalid interview link")

    # Cargar el assessment del líder para seleccionar las preguntas adaptativas
    assessment = session.get(QuickAssessment, member.assessment_id)
    leader_responses = assessment.leader_responses if assessment else {}
    adaptive = select_adaptive_questions(leader_responses, max_count=3)

    return {
        "name": member.name,
        "role": member.role,
        "token": member.token,
        "assessment_id": str(member.assessment_id),
        "submitted": member.submitted_at is not None,
        "responses": member.responses,
        # Preguntas que el miembro debe responder: 10 base + 3 adaptativas
        "questions": FREE_EMPLOYEE_QUESTIONS + adaptive,
        "dimensions": FREE_DIMENSIONS,
    }


@router.post("/interview/{token}/submit")
def submit_member_interview(
    token: str,
    body: MemberRespondRequest,
    session: Session = Depends(get_session),
) -> dict:
    """Public endpoint — no auth. Submit responses for a member by token."""
    member = session.exec(
        select(QuickAssessmentMember).where(QuickAssessmentMember.token == token)
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Invalid interview link")
    if member.submitted_at is not None:
        raise HTTPException(status_code=400, detail="Already submitted")

    for qid in body.responses:
        if qid not in VALID_RESPONSE_IDS:
            raise HTTPException(status_code=400, detail=f"Invalid question: {qid}")

    member.responses = body.responses
    member.submitted_at = datetime.now(timezone.utc)
    session.add(member)

    assessment = session.get(QuickAssessment, member.assessment_id)
    if assessment:
        assessment.responses_count = assessment.responses_count + 1
        session.add(assessment)

    session.commit()
    return {"status": "submitted"}


# ── Public endpoints (no auth — free flow) ───────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
def create_assessment(
    body: QuickAssessmentCreate,
    session: Session = Depends(get_session),
) -> dict:
    """Public — no auth required. Creates an anonymous QuickAssessment."""
    assessment = QuickAssessment(
        org_name=body.org_name,
        org_type=body.org_type,
        size_range=body.size_range,
        owner_id=None,
        leader_responses=body.leader_responses,
    )
    session.add(assessment)
    session.commit()
    session.refresh(assessment)
    return {"id": str(assessment.id)}


@router.get("/{assessment_id}", response_model=QuickAssessmentRead)
def get_assessment(
    assessment_id: UUID,
    session: Session = Depends(get_session),
) -> QuickAssessmentRead:
    """Public — no auth. Anyone with the assessment ID can view it."""
    assessment = session.get(QuickAssessment, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return QuickAssessmentRead.model_validate(assessment)


@router.post("/{assessment_id}/invite")
def invite_members(
    assessment_id: UUID,
    body: InviteMembersRequest,
    session: Session = Depends(get_session),
) -> dict:
    """Public — no auth. Anyone with the assessment ID can invite members."""
    assessment = session.get(QuickAssessment, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    created = 0
    for m in body.members:
        member = QuickAssessmentMember(
            assessment_id=assessment.id,
            name=m.name,
            role=m.role,
            email=m.email,
        )
        session.add(member)
        created += 1

    assessment.member_count = assessment.member_count + created
    session.add(assessment)
    session.commit()
    return {"invited": created}


@router.post("/{assessment_id}/respond")
def respond_member(
    assessment_id: UUID,
    body: MemberRespondRequest,
    session: Session = Depends(get_session),
) -> dict:
    """Public endpoint — no auth required. Member responds via token."""
    member = session.exec(
        select(QuickAssessmentMember).where(
            QuickAssessmentMember.assessment_id == assessment_id,
            QuickAssessmentMember.token == body.token,
        )
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="Invalid token")
    if member.submitted_at is not None:
        raise HTTPException(status_code=400, detail="Already submitted")

    for qid in body.responses:
        if qid not in VALID_RESPONSE_IDS:
            raise HTTPException(status_code=400, detail=f"Invalid question: {qid}")

    member.responses = body.responses
    member.submitted_at = datetime.now(timezone.utc)
    session.add(member)

    assessment = session.get(QuickAssessment, assessment_id)
    if assessment:
        assessment.responses_count = assessment.responses_count + 1
        session.add(assessment)

    session.commit()
    return {"status": "submitted"}


@router.get("/{assessment_id}/score", response_model=QuickAssessmentScoreRead)
def get_score(
    assessment_id: UUID,
    session: Session = Depends(get_session),
) -> QuickAssessmentScoreRead:
    """Public — no auth. Score is accessible via assessment ID."""
    assessment = session.get(QuickAssessment, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Gather submitted member responses
    members = session.exec(
        select(QuickAssessmentMember).where(
            QuickAssessmentMember.assessment_id == assessment_id,
            QuickAssessmentMember.submitted_at.is_not(None),
        )
    ).all()

    member_responses = [m.responses for m in members if m.responses]

    # Compute scores
    scores = _compute_scores(assessment.leader_responses, member_responses)
    assessment.scores = scores
    session.add(assessment)
    session.commit()

    dimensions = [
        DimensionScoreRead(
            dimension=dim_id,
            label=label,
            score=scores.get(dim_id, 0.0),
            max_score=5.0,
        )
        for dim_id, label in FREE_DIMENSIONS.items()
    ]

    return QuickAssessmentScoreRead(
        id=assessment.id,
        org_name=assessment.org_name,
        dimensions=dimensions,
        member_count=assessment.member_count,
        responses_count=len(member_responses),
        created_at=assessment.created_at,
    )


@router.get("/{assessment_id}/members")
def list_members(
    assessment_id: UUID,
    session: Session = Depends(get_session),
) -> list[dict]:
    """Public — no auth. Members list accessible via assessment ID."""
    assessment = session.get(QuickAssessment, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    members = session.exec(
        select(QuickAssessmentMember).where(
            QuickAssessmentMember.assessment_id == assessment_id,
        )
    ).all()

    return [
        {
            "id": str(m.id),
            "name": m.name,
            "role": m.role,
            "email": m.email,
            "token": m.token,
            "submitted": m.submitted_at is not None,
        }
        for m in members
    ]
