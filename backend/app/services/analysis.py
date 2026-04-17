"""
Fase 3: Pipeline de análisis diagnóstico.

Three stages:
1. Quantitative scoring — Likert averages per dimension, per node, global
2. Network analysis — graph metrics from org structure
3. AI narrative — Claude generates insights from open responses + context
"""
from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from app.core.config import settings
from app.models.group import Group
from app.models.interview import Interview
from app.models.member import Member, MemberTokenStatus
from app.models.organization import Organization
from app.questions_premium import PREMIUM_DIMENSIONS, PREMIUM_QUESTIONS

logger = logging.getLogger(__name__)

# ── 1. Quantitative Scoring ─────────────────────────────────────────────────

def compute_scores(
    interviews: list[Interview],
    members: list[Member],
) -> dict[str, Any]:
    """Compute normalised 0-100 scores per dimension from Likert responses."""
    dim_values: dict[str, list[float]] = {d: [] for d in PREMIUM_DIMENSIONS}

    # Map question_id → dimension (only Likert)
    q_dim = {
        q["id"]: q["dimension"]
        for q in PREMIUM_QUESTIONS
        if q["tipo"] == "likert"
    }

    # Per-node scores
    member_node: dict[UUID, UUID | None] = {m.id: m.group_id for m in members}
    node_dim_values: dict[str, dict[str, list[float]]] = {}

    for iv in interviews:
        node_id = str(member_node.get(iv.member_id, "unknown"))
        if node_id not in node_dim_values:
            node_dim_values[node_id] = {d: [] for d in PREMIUM_DIMENSIONS}

        for qid, val in (iv.data or {}).items():
            if qid.startswith("_"):
                continue
            dim = q_dim.get(qid)
            if dim and isinstance(val, (int, float)):
                dim_values[dim].append(float(val))
                node_dim_values[node_id][dim].append(float(val))

    # Global scores normalised to 0-100
    global_scores: dict[str, float] = {}
    for dim, values in dim_values.items():
        if values:
            avg = sum(values) / len(values)  # 1-5 scale
            global_scores[dim] = round((avg / 5) * 100, 1)
        else:
            global_scores[dim] = 0.0

    overall = (
        round(sum(global_scores.values()) / len(global_scores), 1)
        if global_scores
        else 0.0
    )

    # Per-node scores
    per_node: dict[str, dict[str, float]] = {}
    for nid, dims in node_dim_values.items():
        per_node[nid] = {}
        for dim, values in dims.items():
            if values:
                avg = sum(values) / len(values)
                per_node[nid][dim] = round((avg / 5) * 100, 1)
            else:
                per_node[nid][dim] = 0.0

    return {
        "global": global_scores,
        "overall": overall,
        "per_node": per_node,
        "total_responses": len(interviews),
        "dimensions": [
            {
                "id": dim_id,
                "label": label,
                "score": global_scores.get(dim_id, 0.0),
            }
            for dim_id, label in PREMIUM_DIMENSIONS.items()
        ],
    }


# ── 2. Network Analysis ─────────────────────────────────────────────────────

def compute_network_metrics(groups: list[Group]) -> dict[str, Any]:
    """Compute basic graph metrics from the org hierarchy."""
    if not groups:
        return {"total_nodes": 0, "depth": 0, "isolated": 0, "clusters": 0}

    by_id = {str(g.id): g for g in groups}
    children: dict[str, list[str]] = {}
    roots: list[str] = []

    for g in groups:
        gid = str(g.id)
        pid = str(g.parent_group_id) if g.parent_group_id else None
        if pid:
            children.setdefault(pid, []).append(gid)
        else:
            roots.append(gid)

    # Depth
    def calc_depth(node_id: str) -> int:
        kids = children.get(node_id, [])
        if not kids:
            return 0
        return 1 + max(calc_depth(c) for c in kids)

    max_depth = max((calc_depth(r) for r in roots), default=0)

    # Isolated nodes (no parent, no children)
    isolated = [
        gid for gid in by_id
        if gid not in children and str(by_id[gid].parent_group_id or "") not in by_id
        and gid not in roots
    ]

    # Centrality: nodes with most connections (parent + children)
    centrality: dict[str, int] = {}
    for gid in by_id:
        conns = len(children.get(gid, []))
        g = by_id[gid]
        if g.parent_group_id:
            conns += 1
        centrality[gid] = conns

    most_central = sorted(centrality, key=centrality.get, reverse=True)[:5]  # type: ignore

    return {
        "total_nodes": len(groups),
        "depth": max_depth,
        "roots": len(roots),
        "isolated": len(isolated),
        "most_central": [
            {"id": nid, "name": by_id[nid].name, "connections": centrality[nid]}
            for nid in most_central
            if nid in by_id
        ],
    }


# ── 3. AI Narrative via Claude ───────────────────────────────────────────────

SYSTEM_PROMPT = """Eres un experto en diagnóstico organizacional. Analizas entrevistas
y datos cuantitativos para generar informes de diagnóstico institucional.

Tu rol:
- Identificar patrones, fortalezas y debilidades en la organización
- Cruzar información entre dimensiones para encontrar insights no obvios
- Generar recomendaciones accionables priorizadas por impacto
- Escribir en español profesional pero accesible, no académico

Responde SIEMPRE en formato JSON válido con esta estructura exacta:
{
  "resumen_ejecutivo": "2-3 párrafos con los hallazgos más importantes",
  "hallazgos": [
    {
      "dimension": "nombre de la dimensión",
      "titulo": "hallazgo corto",
      "descripcion": "explicación detallada",
      "tipo": "fortaleza" o "debilidad",
      "confianza": "alta", "media" o "baja"
    }
  ],
  "patrones_cruzados": [
    {
      "titulo": "patrón identificado",
      "dimensiones_involucradas": ["dim1", "dim2"],
      "descripcion": "explicación del patrón"
    }
  ],
  "recomendaciones": [
    {
      "titulo": "acción recomendada",
      "descripcion": "detalle de la recomendación",
      "prioridad": "corto_plazo", "mediano_plazo" o "largo_plazo",
      "impacto": "alto", "medio" o "bajo"
    }
  ]
}"""


def _collect_open_responses(interviews: list[Interview]) -> str:
    """Extract open-ended responses grouped by dimension."""
    q_info = {
        q["id"]: {"dimension": q["dimension"], "texto": q["texto"]}
        for q in PREMIUM_QUESTIONS
        if q["tipo"] in ("abierta", "seleccion_multiple")
    }

    by_dim: dict[str, list[str]] = {}
    for iv in interviews:
        for qid, val in (iv.data or {}).items():
            if qid.startswith("_"):
                continue
            info = q_info.get(qid)
            if not info:
                continue
            dim = info["dimension"]
            if isinstance(val, str) and val.strip():
                by_dim.setdefault(dim, []).append(
                    f"Pregunta: {info['texto']}\nRespuesta: {val}"
                )
            elif isinstance(val, list):
                by_dim.setdefault(dim, []).append(
                    f"Pregunta: {info['texto']}\nSelección: {', '.join(val)}"
                )

    parts = []
    for dim_id, label in PREMIUM_DIMENSIONS.items():
        entries = by_dim.get(dim_id, [])
        if entries:
            parts.append(f"\n## {label}\n" + "\n---\n".join(entries))

    return "\n".join(parts) if parts else "(Sin respuestas abiertas disponibles)"


async def generate_narrative(
    org: Organization,
    scores: dict[str, Any],
    network: dict[str, Any],
    interviews: list[Interview],
) -> dict[str, Any]:
    """Call Claude API to generate the diagnostic narrative."""
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — returning placeholder narrative")
        return _placeholder_narrative(scores)

    import anthropic

    open_responses = _collect_open_responses(interviews)

    user_message = f"""Analiza el siguiente diagnóstico organizacional.

## Organización
- Nombre: {org.name}
- Sector: {org.sector}
- Descripción: {org.description}

## Scores Cuantitativos (0-100)
{json.dumps(scores["global"], indent=2, ensure_ascii=False)}

Score global: {scores["overall"]}
Total de entrevistas: {scores["total_responses"]}

## Métricas de Red Organizacional
- Nodos totales: {network["total_nodes"]}
- Profundidad jerárquica: {network["depth"]}
- Nodos raíz: {network["roots"]}

## Respuestas Cualitativas
{open_responses}

Genera el diagnóstico completo en formato JSON."""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        text = message.content[0].text
        # Extract JSON from response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        else:
            logger.error("Claude response did not contain valid JSON")
            return _placeholder_narrative(scores)

    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return _placeholder_narrative(scores)


def _placeholder_narrative(scores: dict[str, Any]) -> dict[str, Any]:
    """Fallback narrative when Claude API is unavailable."""
    dims = scores.get("dimensions", [])
    strongest = max(dims, key=lambda d: d["score"]) if dims else None
    weakest = min(dims, key=lambda d: d["score"]) if dims else None

    return {
        "resumen_ejecutivo": (
            f"Diagnóstico basado en {scores.get('total_responses', 0)} entrevistas. "
            f"Score global: {scores.get('overall', 0)}/100. "
            + (
                f"La dimensión más fuerte es {strongest['label']} ({strongest['score']}/100) "
                f"y la que requiere más atención es {weakest['label']} ({weakest['score']}/100). "
                if strongest and weakest
                else ""
            )
            + "Para un análisis narrativo completo, configure ANTHROPIC_API_KEY."
        ),
        "hallazgos": [
            {
                "dimension": d["label"],
                "titulo": f"Score en {d['label']}",
                "descripcion": f"La dimensión {d['label']} obtuvo un score de {d['score']}/100.",
                "tipo": "fortaleza" if d["score"] >= 60 else "debilidad",
                "confianza": "media",
            }
            for d in dims
        ],
        "patrones_cruzados": [],
        "recomendaciones": [
            {
                "titulo": f"Fortalecer {weakest['label']}" if weakest else "Revisar resultados",
                "descripcion": "Se recomienda una revisión detallada con IA habilitada.",
                "prioridad": "corto_plazo",
                "impacto": "alto",
            }
        ],
        "_placeholder": True,
    }


# ── Orchestrator ─────────────────────────────────────────────────────────────

async def run_diagnosis_pipeline(
    session: Session,
    org_id: UUID,
) -> dict[str, Any]:
    """Execute the full diagnosis pipeline: scoring → network → AI narrative."""
    org = session.get(Organization, org_id)
    if not org:
        raise ValueError(f"Organization {org_id} not found")

    # Fetch completed interviews
    members = session.exec(
        select(Member).where(
            Member.organization_id == org_id,
            Member.token_status == MemberTokenStatus.COMPLETED,
        )
    ).all()
    member_ids = [m.id for m in members]

    interviews = session.exec(
        select(Interview).where(
            Interview.member_id.in_(member_ids),
            Interview.submitted_at.is_not(None),
        )
    ).all()

    # Fetch org structure
    groups = session.exec(
        select(Group).where(Group.organization_id == org_id)
    ).all()

    # Stage 1: Quantitative scoring
    scores = compute_scores(list(interviews), list(members))

    # Stage 2: Network analysis
    network = compute_network_metrics(list(groups))

    # Stage 3: AI narrative
    narrative = await generate_narrative(org, scores, network, list(interviews))

    return {
        "scores": scores,
        "network_metrics": network,
        "narrative": narrative,
    }
