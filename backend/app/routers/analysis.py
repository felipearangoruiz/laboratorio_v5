"""Motor de análisis — endpoints de escritura (script externo) y lectura (frontend).

Arquitectura:
  El script externo NO tiene su propio runtime de IA; usa este backend como
  única fuente de datos y almacenamiento.

  Flujo de una corrida:
    1. POST /organizations/{org_id}/analysis/runs          → abre la corrida
    2. GET  /organizations/{org_id}/analysis/input         → descarga todo el contexto
    3. POST /analysis/runs/{run_id}/nodes/{node_id}        → Paso 1 (×N nodos)
    4. POST /analysis/runs/{run_id}/groups/{node_id}       → Paso 2 (×G grupos)
    5. POST /analysis/runs/{run_id}/org                    → Paso 3
    6. POST /analysis/runs/{run_id}/findings               → Paso 4 + cierra corrida

  El frontend consulta:
    GET /organizations/{org_id}/analysis/status
    GET /organizations/{org_id}/analysis/latest/nodes/{node_id}
    GET /organizations/{org_id}/analysis/latest/groups/{node_id}
"""
from __future__ import annotations

import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.dependencies import get_current_user
from app.db import get_session
from app.models.analysis import (
    AnalysisRun,
    AnalysisRunRead,
    DocumentExtraction,
    EvidenceLink,
    EvidenceLinkCreate,
    Finding,
    FindingCreate,
    FindingRead,
    GroupAnalysis,
    GroupAnalysisCreate,
    GroupAnalysisRead,
    NodeAnalysis,
    NodeAnalysisCreate,
    NodeAnalysisRead,
    OrgAnalysis,
    OrgAnalysisCreate,
    OrgAnalysisRead,
    Recommendation,
    RecommendationCreate,
    RecommendationRead,
)
from app.models.diagnosis import DiagnosisResult
from app.models.document import Document
from app.models.group import Group
from app.models.interview import Interview
from app.models.member import Member, MemberTokenStatus
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.questions_instrument_v2 import QUESTION_BY_ID

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _can_access(user: User, org_id: UUID) -> bool:
    return user.role == UserRole.SUPERADMIN or user.organization_id == org_id


def _require_org(session: Session, org_id: UUID) -> Organization:
    org = session.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


def _require_run(session: Session, run_id: UUID, org_id: UUID | None = None) -> AnalysisRun:
    run = session.get(AnalysisRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    if org_id is not None and run.org_id != org_id:
        raise HTTPException(status_code=403, detail="Run does not belong to this org")
    return run


def _compute_node_scores(
    interviews: list[Interview],
) -> dict[str, dict[str, float]]:
    """Return {dimension: {score: avg, count: n}} for a list of interviews.

    Numeric interpretation:
    - single_select / multi_select answers are 0-based indices; normalised to [0, 1].
    - Answers for questions with ≥2 options are treated as Likert (0 = worst, N-1 = best).
    - Unknown question IDs and non-numeric answers are skipped.
    """
    # dim → list of normalised [0,1] scores
    dim_scores: dict[str, list[float]] = defaultdict(list)

    for iv in interviews:
        for q_id, answer in (iv.data or {}).items():
            q_def = QUESTION_BY_ID.get(q_id)
            if not q_def:
                continue
            dim = q_def.get("dimension")
            if not dim:
                continue
            base = q_def.get("base", {})
            options = base.get("options", [])
            if not options:
                continue
            # answer is an option index (int) or already a float
            try:
                idx = int(answer)
            except (TypeError, ValueError):
                continue
            normalised = idx / (len(options) - 1) if len(options) > 1 else 0.5
            dim_scores[dim].append(max(0.0, min(1.0, normalised)))

    return {
        dim: {
            "score": sum(vals) / len(vals),
            "count": len(vals),
        }
        for dim, vals in dim_scores.items()
        if vals
    }


def _compute_diagnosis_scores(
    groups: list[Group],
    interviews_with_group: list[tuple[Interview, UUID]],
) -> dict[str, Any]:
    """Construye el dict `scores` que persiste DiagnosisResult.

    Sprint 5.A. Shape por dimensión:
      {
        score: avg global normalizado [0,1],
        avg:   alias de score (frontend pre-existente lo consume),
        std:   desviación estándar global por dimensión,
        node_scores: {node_id_str: avg del nodo},
        node_stds:   {node_id_str: std heredado del bucket del nodo},
      }

    Implementa la **OPCIÓN 2** de Sprint 5.A: cada nodo hereda el std
    del bucket al que pertenece (parent_group_id si existe, sí mismo si
    es raíz). Esto captura variación local entre áreas — el frontend la
    usará para modular la intensidad de borde en la capa Análisis.

    `node_stds` es un campo adicional al contrato frontend histórico;
    el typing antiguo lo ignora y los consumers nuevos (Sprint 5.B) lo
    leen explícitamente.
    """
    group_parent: dict[UUID, UUID | None] = {g.id: g.parent_group_id for g in groups}

    def bucket_of(gid: UUID) -> UUID:
        return group_parent.get(gid) or gid

    global_dim_scores: dict[str, list[float]] = defaultdict(list)
    bucket_dim_scores: dict[UUID, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    group_dim_scores: dict[UUID, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for iv, gid in interviews_with_group:
        # Reutilizamos _compute_node_scores para normalizar la interview
        # individual a [0,1] por dimensión.
        iv_scores = _compute_node_scores([iv])
        bid = bucket_of(gid)
        for dim, data in iv_scores.items():
            score = data["score"]
            global_dim_scores[dim].append(score)
            bucket_dim_scores[bid][dim].append(score)
            group_dim_scores[gid][dim].append(score)

    result: dict[str, Any] = {}
    for dim, vals in global_dim_scores.items():
        global_avg = sum(vals) / len(vals) if vals else 0.0
        global_std = statistics.stdev(vals) if len(vals) > 1 else 0.0

        node_scores: dict[str, float] = {}
        node_stds: dict[str, float] = {}
        for g in groups:
            # Score del nodo: promedio de sus interviews en esta dim (si las
            # tiene; en el modelo actual cada unit respondida es proxy de
            # 1 interview, así que el promedio es el valor único).
            gid_scores = group_dim_scores.get(g.id, {}).get(dim)
            if gid_scores:
                node_scores[str(g.id)] = round(sum(gid_scores) / len(gid_scores), 4)

            # Std heredado del bucket (OPCIÓN 2). Aplica a todos los nodos,
            # incluso los que no respondieron ellos mismos, con tal de que
            # el bucket tenga al menos 2 respuestas.
            bucket_vals = bucket_dim_scores.get(bucket_of(g.id), {}).get(dim)
            if bucket_vals and len(bucket_vals) > 1:
                node_stds[str(g.id)] = round(statistics.stdev(bucket_vals), 4)
            elif bucket_vals:
                node_stds[str(g.id)] = 0.0

        result[dim] = {
            "score": round(global_avg, 4),
            "avg": round(global_avg, 4),
            "std": round(global_std, 4),
            "node_scores": node_scores,
            "node_stds": node_stds,
        }

    return result


def _extract_open_responses(interviews: list[Interview]) -> list[str]:
    """Pull all free-text string answers from interview data blobs."""
    texts: list[str] = []
    for iv in interviews:
        for q_id, answer in (iv.data or {}).items():
            if isinstance(answer, str) and len(answer.strip()) > 10:
                texts.append(answer.strip())
    return texts


def _compute_network_metrics(groups: list[Group]) -> dict[str, Any]:
    """Simple degree-centrality metrics from the org graph.

    Returns:
      centrality: {node_id: float}   — normalised degree (0–1)
      bridge_nodes: [node_id]         — have both parent and children
      isolated_nodes: [node_id]       — no parent and no children
    """
    n = len(groups)
    if n == 0:
        return {"centrality": {}, "bridge_nodes": [], "isolated_nodes": []}

    children_count: dict[UUID, int] = defaultdict(int)
    has_parent: set[UUID] = set()

    for g in groups:
        if g.parent_group_id:
            children_count[g.parent_group_id] += 1
            has_parent.add(g.id)

    centrality: dict[str, float] = {}
    bridge_nodes: list[str] = []
    isolated_nodes: list[str] = []
    max_degree = max(1, n - 1)

    for g in groups:
        degree = children_count.get(g.id, 0) + (1 if g.id in has_parent else 0)
        centralised = degree / max_degree
        centrality[str(g.id)] = round(centralised, 4)

        has_children = children_count.get(g.id, 0) > 0
        is_parent = g.id in has_parent

        if has_children and is_parent:
            bridge_nodes.append(str(g.id))
        elif degree == 0:
            isolated_nodes.append(str(g.id))

    return {
        "centrality": centrality,
        "bridge_nodes": bridge_nodes,
        "isolated_nodes": isolated_nodes,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ESCRITURA — llamados por el script externo
# ─────────────────────────────────────────────────────────────────────────────

# ── 1. Abrir corrida ─────────────────────────────────────────────────────────

class CreateRunRequest(BaseModel):
    model_used: str | None = None
    total_nodes: int = 0
    total_groups: int = 0


class CreateRunResponse(BaseModel):
    run_id: UUID
    status: str


@router.post(
    "/organizations/{org_id}/analysis/runs",
    response_model=CreateRunResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["analysis"],
)
def create_run(
    org_id: UUID,
    body: CreateRunRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> CreateRunResponse:
    """Abre una nueva corrida de análisis en status='pending'.

    Llamado por el script externo antes de iniciar el pipeline.
    """
    if not _can_access(current_user, org_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    _require_org(session, org_id)

    run = AnalysisRun(
        org_id=org_id,
        status="running",
        model_used=body.model_used,
        total_nodes=body.total_nodes,
        total_groups=body.total_groups,
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    return CreateRunResponse(run_id=run.id, status=run.status)


# ── 2. Guardar node_analysis (Paso 1) ────────────────────────────────────────

@router.post(
    "/analysis/runs/{run_id}/nodes/{node_id}",
    response_model=NodeAnalysisRead,
    status_code=status.HTTP_201_CREATED,
    tags=["analysis"],
)
def create_node_analysis(
    run_id: UUID,
    node_id: UUID,
    body: NodeAnalysisCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> NodeAnalysisRead:
    """Guarda el node_analysis producido en el Paso 1 del pipeline."""
    run = _require_run(session, run_id)
    if not _can_access(current_user, run.org_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    node = NodeAnalysis(
        run_id=run_id,
        org_id=run.org_id,
        node_id=node_id,
        signals_positive=body.signals_positive,
        signals_tension=body.signals_tension,
        themes=body.themes,
        dimensions_touched=body.dimensions_touched,
        evidence_type=body.evidence_type,
        emotional_intensity=body.emotional_intensity,
        key_quotes=body.key_quotes,
        context_notes_used=body.context_notes_used,
        confidence=body.confidence,
    )
    session.add(node)
    session.commit()
    session.refresh(node)

    return NodeAnalysisRead.model_validate(node)


# ── 3. Guardar group_analysis (Paso 2) ───────────────────────────────────────

@router.post(
    "/analysis/runs/{run_id}/groups/{node_id}",
    response_model=GroupAnalysisRead,
    status_code=status.HTTP_201_CREATED,
    tags=["analysis"],
)
def create_group_analysis(
    run_id: UUID,
    node_id: UUID,
    body: GroupAnalysisCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> GroupAnalysisRead:
    """Guarda el group_analysis producido en el Paso 2 del pipeline."""
    run = _require_run(session, run_id)
    if not _can_access(current_user, run.org_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    ga = GroupAnalysis(
        run_id=run_id,
        org_id=run.org_id,
        node_id=node_id,
        patterns_internal=body.patterns_internal,
        dominant_themes=body.dominant_themes,
        tension_level=body.tension_level,
        scores_by_dimension=body.scores_by_dimension,
        gap_leader_team=body.gap_leader_team,
        coverage=body.coverage,
        confidence=body.confidence,
    )
    session.add(ga)
    session.commit()
    session.refresh(ga)

    return GroupAnalysisRead.model_validate(ga)


# ── 4. Guardar org_analysis (Paso 3) ─────────────────────────────────────────

@router.post(
    "/analysis/runs/{run_id}/org",
    response_model=OrgAnalysisRead,
    status_code=status.HTTP_201_CREATED,
    tags=["analysis"],
)
def create_org_analysis(
    run_id: UUID,
    body: OrgAnalysisCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> OrgAnalysisRead:
    """Guarda el org_analysis producido en el Paso 3 del pipeline."""
    run = _require_run(session, run_id)
    if not _can_access(current_user, run.org_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    oa = OrgAnalysis(
        run_id=run_id,
        org_id=run.org_id,
        cross_patterns=body.cross_patterns,
        contradictions=body.contradictions,
        structural_risks=body.structural_risks,
        dimension_scores=body.dimension_scores,
        network_metrics=body.network_metrics,
        confidence=body.confidence,
    )
    session.add(oa)
    session.commit()
    session.refresh(oa)

    return OrgAnalysisRead.model_validate(oa)


# ── 5. Guardar hallazgos + cerrar corrida (Paso 4) ───────────────────────────

class FindingWithEvidence(BaseModel):
    """Un hallazgo con sus links de evidencia opcionales."""
    title: str
    description: str
    type: str
    severity: str = "media"
    dimensions: list[str] = []
    node_ids: list[str] = []
    confidence: float = 0.5
    confidence_rationale: str | None = None
    evidence_links: list[EvidenceLinkCreate] = []


class RecommendationIn(BaseModel):
    """Recomendación sin run_id/org_id (se injectan del run)."""
    finding_index: int | None = None   # índice en la lista de findings enviada
    title: str
    description: str
    priority: int = 99
    impact: str = "medio"
    effort: str = "medio"
    horizon: str = "corto"
    node_ids: list[str] = []


class SubmitFindingsRequest(BaseModel):
    findings: list[FindingWithEvidence]
    recommendations: list[RecommendationIn] = []
    narrative_md: str = ""
    narrative_sections: dict[str, Any] | None = None
    executive_summary: str = ""


class SubmitFindingsResponse(BaseModel):
    run_id: UUID
    status: str
    findings_created: int
    recommendations_created: int
    diagnosis_id: UUID


@router.post(
    "/analysis/runs/{run_id}/findings",
    response_model=SubmitFindingsResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["analysis"],
)
def submit_findings(
    run_id: UUID,
    body: SubmitFindingsRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> SubmitFindingsResponse:
    """Paso 4 — guarda hallazgos + recomendaciones y cierra la corrida.

    También crea/actualiza el DiagnosisResult consolidado que consume el
    frontend en la capa Resultados.
    """
    run = _require_run(session, run_id)
    if not _can_access(current_user, run.org_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    now = datetime.now(timezone.utc)

    # ── Guardar Finding rows ───────────────────────────────────────────
    saved_findings: list[Finding] = []
    for f_in in body.findings:
        f = Finding(
            run_id=run_id,
            org_id=run.org_id,
            title=f_in.title,
            description=f_in.description,
            type=f_in.type,
            severity=f_in.severity,
            dimensions=f_in.dimensions,
            node_ids=f_in.node_ids,
            confidence=f_in.confidence,
            confidence_rationale=f_in.confidence_rationale,
        )
        session.add(f)
        session.flush()   # get f.id before evidence links

        for ev in f_in.evidence_links:
            el = EvidenceLink(
                finding_id=f.id,
                node_analysis_id=ev.node_analysis_id,
                group_analysis_id=ev.group_analysis_id,
                quote=ev.quote,
                evidence_type=ev.evidence_type,
            )
            session.add(el)

        saved_findings.append(f)

    # ── Guardar Recommendation rows ────────────────────────────────────
    saved_recs: list[Recommendation] = []
    for r_in in body.recommendations:
        finding_id: UUID | None = None
        if r_in.finding_index is not None and 0 <= r_in.finding_index < len(saved_findings):
            finding_id = saved_findings[r_in.finding_index].id

        r = Recommendation(
            run_id=run_id,
            org_id=run.org_id,
            finding_id=finding_id,
            title=r_in.title,
            description=r_in.description,
            priority=r_in.priority,
            impact=r_in.impact,
            effort=r_in.effort,
            horizon=r_in.horizon,
            node_ids=r_in.node_ids,
        )
        session.add(r)
        saved_recs.append(r)

    # ── Crear DiagnosisResult consolidado (para la capa Resultados) ────
    # Formato compatible con DiagnosisResultRead y el frontend existente.
    findings_payload = [
        {
            "id": str(f.id),
            "title": f.title,
            "description": f.description,
            "type": f.type,
            "severity": f.severity,
            "dimensions": f.dimensions,
            "node_ids": f.node_ids,
            "confidence": f.confidence,
            "confidence_rationale": f.confidence_rationale,
        }
        for f in saved_findings
    ]
    recs_payload = [
        {
            "id": str(r.id),
            "title": r.title,
            "description": r.description,
            "priority": r.priority,
            "impact": r.impact,
            "effort": r.effort,
            "horizon": r.horizon,
            "node_ids": r.node_ids,
        }
        for r in saved_recs
    ]

    # ── Sprint 5.A — scores con std heredado del bucket (OPCIÓN 2) ─────
    # Poblamos el dict `scores` que históricamente quedaba vacío. El
    # frontend de 5.B lo consumirá para renderizar intensidades por nodo
    # por dimensión.
    groups_for_scores = session.exec(
        select(Group).where(Group.organization_id == run.org_id)
    ).all()
    completed_members_scores = session.exec(
        select(Member).where(
            Member.organization_id == run.org_id,
            Member.token_status == MemberTokenStatus.COMPLETED,
        )
    ).all()
    member_group_map_scores = {
        m.id: m.group_id for m in completed_members_scores if m.group_id
    }
    interviews_with_group: list[tuple[Interview, UUID]] = []
    if member_group_map_scores:
        ivs = session.exec(
            select(Interview).where(Interview.member_id.in_(member_group_map_scores.keys()))
        ).all()
        for iv in ivs:
            gid = member_group_map_scores.get(iv.member_id)
            if gid:
                interviews_with_group.append((iv, gid))

    scores_dict = _compute_diagnosis_scores(groups_for_scores, interviews_with_group)

    diag = DiagnosisResult(
        organization_id=run.org_id,
        status="ready",
        scores=scores_dict,
        findings=findings_payload,
        recommendations=recs_payload,
        narrative_md=body.narrative_md,
        narrative_sections=body.narrative_sections,
        structure_snapshot={"run_id": str(run_id), "executive_summary": body.executive_summary},
        completed_at=now,
    )
    session.add(diag)

    # ── Cerrar la corrida ──────────────────────────────────────────────
    run.status = "completed"
    run.completed_at = now
    session.add(run)

    session.commit()
    session.refresh(diag)

    return SubmitFindingsResponse(
        run_id=run_id,
        status=run.status,
        findings_created=len(saved_findings),
        recommendations_created=len(saved_recs),
        diagnosis_id=diag.id,
    )


# ─────────────────────────────────────────────────────────────────────────────
# LECTURA — llamados por el frontend
# ─────────────────────────────────────────────────────────────────────────────

# ── GET /organizations/{org_id}/analysis/input ───────────────────────────────

@router.get(
    "/organizations/{org_id}/analysis/input",
    response_model=dict[str, Any],
    tags=["analysis"],
)
def get_analysis_input(
    org_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Devuelve el bundle completo que necesita el script externo para el pipeline.

    Response schema
    ───────────────
    {
      "organization": {
        "id": str,
        "name": str,
        "description": str,
        "sector": str,
        "org_structure_type": str,       # "areas" | "personas" | etc.
        "strategic_objectives": str,
        "strategic_concerns": str,
        "key_questions": str,
        "additional_context": str
      },
      "structure": {
        "nodes": [
          {
            "id": str,
            "name": str,
            "role": str,                 # tarea_general
            "area": str,
            "node_type": str,            # "area" | "persona"
            "nivel_jerarquico": int|null,
            "tipo_nivel": str|null,
            "parent_id": str|null,
            "context_notes": str|null,
            "email": str,
            "has_interview": bool        # true if a completed interview exists
          }
        ],
        "total_nodes": int,
        "total_with_interview": int
      },
      "interviews": {
        "by_node": {
          "<group_id>": {
            "quantitative_scores": {     # {dimension: {score, count}}
              "<dimension>": {"score": float, "count": int}
            },
            "open_responses": [str],     # anonimizados
            "coverage": float,           # 0–1 (completadas / total esperadas)
            "respondents": [             # anonimizados: solo rol + área
              {"role": str, "area": str}
            ]
          }
        },
        "total_completed": int
      },
      "documents": [
        {
          "id": str,
          "label": str,
          "doc_type": str,
          "filename": str,
          "created_at": str
        }
      ],
      "network_metrics": {
        "centrality": {"<node_id>": float},
        "bridge_nodes": [str],
        "isolated_nodes": [str]
      }
    }
    """
    if not _can_access(current_user, org_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    org = _require_org(session, org_id)

    # ── Nodos ──────────────────────────────────────────────────────────
    groups = session.exec(
        select(Group).where(Group.organization_id == org_id)
    ).all()
    group_map = {g.id: g for g in groups}

    # ── Miembros con entrevista completada ─────────────────────────────
    completed_members = session.exec(
        select(Member).where(
            Member.organization_id == org_id,
            Member.token_status == MemberTokenStatus.COMPLETED,
        )
    ).all()
    member_group_map = {m.id: m.group_id for m in completed_members}
    member_role_map = {m.id: m.role_label for m in completed_members}
    member_ids = [m.id for m in completed_members]

    # ── Entrevistas agrupadas por nodo ─────────────────────────────────
    interviews_raw: list[Interview] = []
    if member_ids:
        interviews_raw = session.exec(
            select(Interview).where(Interview.member_id.in_(member_ids))
        ).all()

    # Agrupa interviews por group_id
    interviews_by_group: dict[UUID, list[Interview]] = defaultdict(list)
    for iv in interviews_raw:
        gid = member_group_map.get(iv.member_id)
        if gid:
            interviews_by_group[gid].append(iv)

    # ── Todos los miembros (para coverage) ─────────────────────────────
    all_members = session.exec(
        select(Member).where(Member.organization_id == org_id)
    ).all()
    members_per_group: dict[UUID, int] = defaultdict(int)
    for m in all_members:
        if m.group_id:
            members_per_group[m.group_id] += 1

    # ── Construir nodo con has_interview ───────────────────────────────
    nodes_with_interview: set[UUID] = set(interviews_by_group.keys())
    nodes_out = []
    for g in groups:
        nodes_out.append({
            "id": str(g.id),
            "name": g.name,
            "role": g.tarea_general,
            "area": g.area,
            "node_type": g.node_type,
            "nivel_jerarquico": g.nivel_jerarquico,
            "tipo_nivel": g.tipo_nivel,
            "parent_id": str(g.parent_group_id) if g.parent_group_id else None,
            "context_notes": g.context_notes,
            "email": g.email or "",
            "has_interview": g.id in nodes_with_interview,
        })

    # ── Entrevistas por nodo — scores + texto abierto ─────────────────
    interviews_out: dict[str, Any] = {}
    for gid, ivs in interviews_by_group.items():
        g = group_map.get(gid)
        node_area = g.area if g else ""
        total_members = max(1, members_per_group.get(gid, 1))
        coverage = len(ivs) / total_members

        interviews_out[str(gid)] = {
            "quantitative_scores": _compute_node_scores(ivs),
            "open_responses": _extract_open_responses(ivs),
            "coverage": round(coverage, 3),
            "respondents": [
                {
                    "role": member_role_map.get(iv.member_id, ""),
                    "area": node_area,
                }
                for iv in ivs
            ],
        }

    # ── Documentos (sin contenido binario) ────────────────────────────
    docs = session.exec(
        select(Document).where(Document.organization_id == org_id)
    ).all()
    documents_out = [
        {
            "id": str(d.id),
            "label": d.label,
            "doc_type": d.doc_type,
            "filename": d.filename,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]

    # ── Métricas de red ────────────────────────────────────────────────
    network_metrics = _compute_network_metrics(groups)

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
            "nodes": nodes_out,
            "total_nodes": len(nodes_out),
            "total_with_interview": len(nodes_with_interview),
        },
        "interviews": {
            "by_node": interviews_out,
            "total_completed": len(member_ids),
        },
        "documents": documents_out,
        "network_metrics": network_metrics,
    }


# ── GET /organizations/{org_id}/analysis/latest/nodes/{node_id} ──────────────

@router.get(
    "/organizations/{org_id}/analysis/latest/nodes/{node_id}",
    response_model=NodeAnalysisRead | None,
    tags=["analysis"],
)
def get_latest_node_analysis(
    org_id: UUID,
    node_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> NodeAnalysisRead | None:
    """Devuelve el node_analysis más reciente para un nodo dado.

    Incluye signals, themes, key_quotes, confidence.
    Útil para el panel lateral en capa Análisis.
    """
    if not _can_access(current_user, org_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    # Latest completed run for this org
    run = session.exec(
        select(AnalysisRun)
        .where(AnalysisRun.org_id == org_id, AnalysisRun.status == "completed")
        .order_by(AnalysisRun.started_at.desc())
    ).first()

    if not run:
        return None

    node = session.exec(
        select(NodeAnalysis)
        .where(NodeAnalysis.run_id == run.id, NodeAnalysis.node_id == node_id)
    ).first()

    return NodeAnalysisRead.model_validate(node) if node else None


# ── GET /organizations/{org_id}/analysis/latest/groups/{node_id} ─────────────

@router.get(
    "/organizations/{org_id}/analysis/latest/groups/{node_id}",
    response_model=GroupAnalysisRead | None,
    tags=["analysis"],
)
def get_latest_group_analysis(
    org_id: UUID,
    node_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> GroupAnalysisRead | None:
    """Devuelve el group_analysis más reciente para un grupo dado.

    Incluye patrones internos, tension_level, scores_by_dimension.
    """
    if not _can_access(current_user, org_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    run = session.exec(
        select(AnalysisRun)
        .where(AnalysisRun.org_id == org_id, AnalysisRun.status == "completed")
        .order_by(AnalysisRun.started_at.desc())
    ).first()

    if not run:
        return None

    ga = session.exec(
        select(GroupAnalysis)
        .where(GroupAnalysis.run_id == run.id, GroupAnalysis.node_id == node_id)
    ).first()

    return GroupAnalysisRead.model_validate(ga) if ga else None


# ── GET /organizations/{org_id}/analysis/status ──────────────────────────────

class AnalysisStatusResponse(BaseModel):
    status: str          # none | pending | running | completed | failed
    run_id: UUID | None = None
    started_at: str | None = None
    completed_at: str | None = None
    total_nodes: int = 0
    total_groups: int = 0
    error_message: str | None = None


@router.get(
    "/organizations/{org_id}/analysis/status",
    response_model=AnalysisStatusResponse,
    tags=["analysis"],
)
def get_analysis_status(
    org_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> AnalysisStatusResponse:
    """Devuelve el estado del analysis_run más reciente.

    Si no existe ninguna corrida, devuelve {"status": "none"}.
    El frontend lo usa para mostrar el estado en la capa Resultados
    (DiagnosisGate y la barra de progreso de corrida).
    """
    if not _can_access(current_user, org_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    run = session.exec(
        select(AnalysisRun)
        .where(AnalysisRun.org_id == org_id)
        .order_by(AnalysisRun.started_at.desc())
    ).first()

    if not run:
        return AnalysisStatusResponse(status="none")

    return AnalysisStatusResponse(
        status=run.status,
        run_id=run.id,
        started_at=run.started_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        total_nodes=run.total_nodes,
        total_groups=run.total_groups,
        error_message=run.error_message,
    )


# ─────────────────────────────────────────────────────────────────────────────
# CURL de referencia — Paso 1: abrir corrida
# ─────────────────────────────────────────────────────────────────────────────
#
# export ORG_ID="<uuid>"
# export TOKEN="<jwt>"
# export BASE="http://localhost:8000"
#
# curl -s -X POST "$BASE/organizations/$ORG_ID/analysis/runs" \
#      -H "Authorization: Bearer $TOKEN" \
#      -H "Content-Type: application/json" \
#      -d '{"model_used": "gpt-4o-mini", "total_nodes": 8, "total_groups": 3}' \
#      | python3 -m json.tool
#
# Respuesta esperada:
# {
#   "run_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
#   "status": "running"
# }
