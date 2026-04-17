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
from app.questions_free import FREE_DIMENSIONS, FREE_QUESTION_IDS, FREE_QUESTIONS

router = APIRouter()


def _compute_scores(
    leader_responses: dict,
    member_responses_list: list[dict],
) -> dict:
    """Compute average score per dimension combining leader + member responses."""
    dimension_scores: dict[str, list[float]] = {dim: [] for dim in FREE_DIMENSIONS}

    # Map question_id → dimension
    q_dim = {q["id"]: q["dimension"] for q in FREE_QUESTIONS}

    # Add leader responses
    for qid, val in leader_responses.items():
        dim = q_dim.get(qid)
        if dim and isinstance(val, (int, float)):
            dimension_scores[dim].append(float(val))

    # Add member responses
    for resp in member_responses_list:
        for qid, val in resp.items():
            dim = q_dim.get(qid)
            if dim and isinstance(val, (int, float)):
                dimension_scores[dim].append(float(val))

    result = {}
    for dim, values in dimension_scores.items():
        if values:
            result[dim] = round(sum(values) / len(values), 2)
        else:
            result[dim] = 0.0

    return result


# ── Public endpoints (no auth) — MUST come before /{assessment_id} routes ──

@router.get("/interview/{token}")
def get_member_interview(
    token: str,
    session: Session = Depends(get_session),
) -> dict:
    """Public endpoint — no auth. Fetch interview state for a member by token."""
    member = session.exec(
        select(QuickAssessmentMember).where(QuickAssessmentMember.token == token)
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Invalid interview link")

    return {
        "name": member.name,
        "role": member.role,
        "token": member.token,
        "assessment_id": str(member.assessment_id),
        "submitted": member.submitted_at is not None,
        "responses": member.responses,
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

    for qid, val in body.responses.items():
        if qid not in FREE_QUESTION_IDS:
            raise HTTPException(status_code=400, detail=f"Invalid question: {qid}")
        if not isinstance(val, int) or val < 1 or val > 5:
            raise HTTPException(status_code=400, detail=f"Invalid value for {qid}: must be 1-5")

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

    for qid, val in body.responses.items():
        if qid not in FREE_QUESTION_IDS:
            raise HTTPException(status_code=400, detail=f"Invalid question: {qid}")
        if not isinstance(val, int) or val < 1 or val > 5:
            raise HTTPException(status_code=400, detail=f"Invalid value for {qid}: must be 1-5")

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
