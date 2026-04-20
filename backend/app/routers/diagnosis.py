"""Diagnosis endpoints — receive results from external Codex processor, serve to frontend.

Architecture: the backend does NOT run analysis. The external Codex processor:
  1. Calls GET /diagnosis/input to fetch org data
  2. Runs scoring + LLM + network analysis externally
  3. Calls POST /diagnosis to store the completed result

The frontend then reads via GET /diagnosis/latest and GET /diagnosis/{id}/node/{node_id}.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.dependencies import get_current_user
from app.db import get_session
from app.models.diagnosis import DiagnosisCreate, DiagnosisResult, DiagnosisResultRead
from app.models.document import Document
from app.models.group import Group
from app.models.interview import Interview
from app.models.member import Member, MemberTokenStatus
from app.models.organization import Organization
from app.models.user import User, UserRole

router = APIRouter()


def _can_access(user: User, org_id: UUID) -> bool:
    return user.role == UserRole.SUPERADMIN or user.organization_id == org_id


# ─────────────────────────────────────────────────────────────────────────────
# GET /organizations/{org_id}/diagnosis/latest
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/organizations/{org_id}/diagnosis/latest",
    response_model=DiagnosisResultRead | None,
    tags=["diagnosis"],
)
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


# ─────────────────────────────────────────────────────────────────────────────
# POST /organizations/{org_id}/diagnosis
# Called by the external Codex processor to store completed results
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/organizations/{org_id}/diagnosis",
    response_model=DiagnosisResultRead,
    status_code=status.HTTP_201_CREATED,
    tags=["diagnosis"],
)
def create_diagnosis(
    org_id: UUID,
    body: DiagnosisCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> DiagnosisResultRead:
    """Receive a completed diagnosis from the external processor.

    Sets status='ready' and records completed_at automatically.
    The Codex script authenticates with the org admin's JWT token.
    """
    if not _can_access(current_user, org_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    result = DiagnosisResult(
        organization_id=org_id,
        status="ready",
        scores=body.scores,
        findings=body.findings,
        recommendations=body.recommendations,
        narrative_md=body.narrative_md,
        structure_snapshot=body.structure_snapshot,
        completed_at=datetime.now(timezone.utc),
    )
    session.add(result)
    session.commit()
    session.refresh(result)
    return DiagnosisResultRead.model_validate(result)


# ─────────────────────────────────────────────────────────────────────────────
# GET /organizations/{org_id}/diagnosis/{diagnosis_id}/node/{node_id}
# Returns findings, recommendations, and scores filtered for a specific node
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/organizations/{org_id}/diagnosis/{diagnosis_id}/node/{node_id}",
    response_model=dict[str, Any],
    tags=["diagnosis"],
)
def get_node_diagnosis(
    org_id: UUID,
    diagnosis_id: UUID,
    node_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Return analysis data scoped to a single canvas node.

    Supports the Resultados layer: clicking a node opens this data in the
    side panel (findings, recommendations, per-dimension scores vs. org avg).
    """
    if not _can_access(current_user, org_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    result = session.get(DiagnosisResult, diagnosis_id)
    if not result or result.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Diagnosis not found")

    # Findings that mention this node
    node_findings = [
        f for f in (result.findings or [])
        if node_id in (f.get("node_ids") or [])
    ]

    # Recommendations that mention this node
    node_recommendations = [
        r for r in (result.recommendations or [])
        if node_id in (r.get("node_ids") or [])
    ]

    # Per-dimension score for this node vs. org average
    node_scores: dict[str, Any] = {}
    for dimension, dim_data in (result.scores or {}).items():
        if not isinstance(dim_data, dict):
            continue
        node_score_val = (dim_data.get("node_scores") or {}).get(node_id)
        if node_score_val is not None:
            node_scores[dimension] = {
                "score": node_score_val,
                "avg": dim_data.get("avg"),
                "std": dim_data.get("std"),
            }

    return {
        "node_id": node_id,
        "scores": node_scores,
        "findings": node_findings,
        "recommendations": node_recommendations,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /organizations/{org_id}/diagnosis/input
# Data bundle for the external Codex processor
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/organizations/{org_id}/diagnosis/input",
    response_model=dict[str, Any],
    tags=["diagnosis"],
)
def get_diagnosis_input(
    org_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Return all data needed for the external Codex processor to run analysis.

    Includes:
    - Organization metadata (name, sector, objectives, context)
    - Structure: all nodes with hierarchy, areas, roles, context notes
    - Interview responses: aggregated by node, anonymized (role + area only, no names)
    - Documents metadata (no binary content)

    The processor calls this endpoint, runs scoring + LLM + network analysis,
    then posts the result back to POST /organizations/{org_id}/diagnosis.
    """
    if not _can_access(current_user, org_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    # ── Organization ──
    org = session.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # ── Structure ──
    groups = session.exec(
        select(Group).where(Group.organization_id == org_id)
    ).all()
    group_map = {g.id: g for g in groups}

    nodes = [
        {
            "id": str(g.id),
            "name": g.name,
            "role": g.tarea_general,
            "area": g.area,
            "node_type": g.node_type,
            "nivel_jerarquico": g.nivel_jerarquico,
            "parent_id": str(g.parent_group_id) if g.parent_group_id else None,
            "context_notes": g.context_notes,
            "has_email": bool(g.email and g.email.strip()),
        }
        for g in groups
    ]

    # ── Interview responses — anonymized, aggregated by node ──
    completed_members = session.exec(
        select(Member).where(
            Member.organization_id == org_id,
            Member.token_status == MemberTokenStatus.COMPLETED,
        )
    ).all()

    member_ids = [m.id for m in completed_members]
    member_group_map = {m.id: m.group_id for m in completed_members}
    member_role_map = {m.id: m.role_label for m in completed_members}

    interviews_by_node: dict[str, list[dict[str, Any]]] = {}
    if member_ids:
        interviews = session.exec(
            select(Interview).where(Interview.member_id.in_(member_ids))
        ).all()

        for iv in interviews:
            gid = member_group_map.get(iv.member_id)
            node_key = str(gid) if gid else "unassigned"
            node_area = (group_map[gid].area or "") if gid and gid in group_map else ""

            interviews_by_node.setdefault(node_key, []).append({
                # Anonymized: role + area only, no name or email
                "role": member_role_map.get(iv.member_id, ""),
                "area": node_area,
                "data": iv.data,
            })

    # ── Documents metadata (no binary content) ──
    docs = session.exec(
        select(Document).where(Document.organization_id == org_id)
    ).all()

    documents = [
        {
            "id": str(d.id),
            "label": d.label,
            "doc_type": d.doc_type,
            "filename": d.filename,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]

    return {
        "organization": {
            "id": str(org.id),
            "name": org.name,
            "description": org.description,
            "sector": org.sector,
            "org_structure_type": org.org_structure_type,
            "strategic_objectives": org.strategic_objectives,
            "strategic_concerns": org.strategic_concerns,
            "key_questions": org.key_questions,
            "additional_context": org.additional_context,
        },
        "structure": {
            "nodes": nodes,
            "total_nodes": len(nodes),
        },
        "interviews": {
            "by_node": interviews_by_node,
            "total_completed": len(member_ids),
        },
        "documents": documents,
    }
