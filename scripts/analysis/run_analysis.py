#!/usr/bin/env python3
"""Motor de análisis — script principal.

Ejecuta el pipeline de 4 pasos sobre una organización y guarda los
resultados en el backend vía sus endpoints REST.

Uso básico:
    python run_analysis.py --org-id <uuid> --base-url http://localhost:8000

Con resume (si falló en el paso 3):
    python run_analysis.py --org-id <uuid> --resume <run_id>

Variables de entorno requeridas:
    OPENAI_API_KEY       — clave de OpenAI
    DIAGNOSIS_API_TOKEN  — JWT de un usuario admin de la org

Dependencias:
    pip install openai requests python-dotenv
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from openai import OpenAI

# ── Cargar variables de entorno ───────────────────────────────────────────
# Orden de prioridad:
#   1. .env.test  (generado por seed_mock_org.py — contiene ORG_ID y ADMIN_TOKEN)
#   2. .env       (configuración manual del usuario)
#   3. Variables del sistema (export DIAGNOSIS_API_TOKEN=...)
_env_test    = Path(__file__).parent / ".env.test"
_env_default = Path(__file__).parent / ".env"

if _env_test.exists():
    load_dotenv(dotenv_path=_env_test, override=False)
if _env_default.exists():
    load_dotenv(dotenv_path=_env_default, override=False)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Acepta tanto DIAGNOSIS_API_TOKEN (nombre canónico) como ADMIN_TOKEN
# (nombre que escribe seed_mock_org.py en .env.test)
DIAGNOSIS_API_TOKEN = (
    os.environ.get("DIAGNOSIS_API_TOKEN")
    or os.environ.get("ADMIN_TOKEN")
    or ""
)

# ── Modelos según contrato MOTOR_ANALISIS.md sección 3 ────────────────────
MODEL_PASO1 = "gpt-4o-mini"
MODEL_PASO2 = "gpt-4o-mini"
MODEL_PASO3 = "gpt-4o"
MODEL_PASO4 = "gpt-4o"

# ── Directorio del script ──────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
PROMPTS_DIR = SCRIPT_DIR / "prompts"


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────────────────────────────────────────

def _load_prompt(filename: str) -> str:
    """Carga un archivo de prompt desde prompts/."""
    path = PROMPTS_DIR / filename
    return path.read_text(encoding="utf-8")


def _state_path(run_id: str) -> Path:
    return SCRIPT_DIR / f".state_{run_id}.json"


def _save_state(state: dict) -> None:
    path = _state_path(state["run_id"])
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _load_state(run_id: str) -> dict | None:
    path = _state_path(run_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _log(msg: str) -> None:
    print(f"[análisis] {msg}", flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# HTTP client helpers
# ─────────────────────────────────────────────────────────────────────────────

class APIError(Exception):
    pass


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {DIAGNOSIS_API_TOKEN}",
        "Content-Type": "application/json",
    }


def _get(base_url: str, path: str) -> Any:
    url = f"{base_url.rstrip('/')}{path}"
    r = requests.get(url, headers=_headers(), timeout=30)
    if not r.ok:
        raise APIError(f"GET {path} → {r.status_code}: {r.text[:300]}")
    return r.json()


def _post(base_url: str, path: str, body: dict) -> Any:
    url = f"{base_url.rstrip('/')}{path}"
    r = requests.post(url, headers=_headers(), json=body, timeout=60)
    if not r.ok:
        raise APIError(f"POST {path} → {r.status_code}: {r.text[:300]}")
    return r.json()


# ─────────────────────────────────────────────────────────────────────────────
# OpenAI call — siempre devuelve JSON parseado
# ─────────────────────────────────────────────────────────────────────────────

def _call_llm(client: OpenAI, model: str, system_prompt: str, user_content: str) -> dict | list:
    """Llama al LLM y parsea el JSON de respuesta.

    Reintenta hasta 2 veces si la respuesta no es JSON válido.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            raw = resp.choices[0].message.content or "{}"
            return json.loads(raw)
        except json.JSONDecodeError as e:
            if attempt == 2:
                raise APIError(f"LLM devolvió JSON inválido tras 3 intentos: {e}")
            _log(f"  ⚠ JSON inválido (intento {attempt+1}), reintentando…")
            time.sleep(2)
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# Cálculo de confianza — fórmula de MOTOR_ANALISIS.md sección 4
# (aplicada a hallazgos del Paso 4, no al LLM)
# ─────────────────────────────────────────────────────────────────────────────

def _compute_confidence(
    pattern_group_count: int,      # en cuántos grupos aparece este patrón
    has_quanti_quali_convergence: bool,
    coverage: float,               # 0–1
    score_std: float | None = None,
    only_one_node: bool = False,
) -> float:
    """Implementa la fórmula de confianza del contrato técnico.

    Base: 0.50
    + si el patrón aparece en más de un grupo: +0.20
    + si hay convergencia cuanti + cuali: +0.10
    + si coverage > 70%: +0.10
    - si coverage < 40%: -0.20
    - si alta dispersión (std > 1.5): -0.10
    - si solo un nodo lo reporta: -0.20
    ────────────────────────────────────────────
    Máximo: 0.95   Mínimo: 0.10
    """
    c = 0.50
    if pattern_group_count > 1:
        c += 0.20
    if has_quanti_quali_convergence:
        c += 0.10
    if coverage > 0.70:
        c += 0.10
    if coverage < 0.40:
        c -= 0.20
    if score_std is not None and score_std > 1.5:
        c -= 0.10
    if only_one_node:
        c -= 0.20
    return round(max(0.10, min(0.95, c)), 2)


# ─────────────────────────────────────────────────────────────────────────────
# PASO 1 — Extracción por nodo
# ─────────────────────────────────────────────────────────────────────────────

def _run_paso1(
    client: OpenAI,
    base_url: str,
    run_id: str,
    input_data: dict,
    state: dict,
) -> dict[str, str]:
    """Procesa cada nodo con entrevista completada. Devuelve {group_id: node_analysis_id}."""
    prompt_template = _load_prompt("paso1_nodo.txt")
    results: dict[str, str] = state.get("node_analyses", {})

    nodes = input_data["structure"]["nodes"]
    interviews_by_node = input_data["interviews"]["by_node"]
    docs = input_data.get("documents", [])

    nodes_with_data = [n for n in nodes if n.get("has_interview")]
    _log(f"Paso 1 — {len(nodes_with_data)} nodos con entrevista")

    for node in nodes_with_data:
        gid = node["id"]
        if gid in results:
            _log(f"  ↷ {node['name']} (ya procesado, skip)")
            continue

        interview_data = interviews_by_node.get(gid, {})
        quanti_scores = {
            dim: round(v["score"], 3)
            for dim, v in interview_data.get("quantitative_scores", {}).items()
        }

        # Documentos asociados a este nodo (por ahora todos son org-level)
        doc_summaries = [
            {"type": d["doc_type"], "key_content": f"{d['label']} ({d['filename']})"}
            for d in docs
        ]

        llm_input = {
            "node_role": node.get("role") or node.get("tarea_general") or "",
            "node_level": node.get("nivel_jerarquico") or 0,
            "context_notes": node.get("context_notes"),
            "quantitative_responses": quanti_scores,
            "open_responses": interview_data.get("open_responses", []),
            "documents": doc_summaries,
        }

        system_prompt = prompt_template.replace("{{input_json}}", json.dumps(llm_input, ensure_ascii=False, indent=2))

        _log(f"  → {node['name']} ({MODEL_PASO1})…")
        result = _call_llm(client, MODEL_PASO1, system_prompt, "Analiza este nodo y devuelve el JSON.")

        body = {
            "run_id": run_id,
            "org_id": input_data["organization"]["id"],
            "group_id": gid,
            "signals_positive": result.get("signals_positive", []),
            "signals_tension": result.get("signals_tension", []),
            "themes": result.get("themes", []),
            "dimensions_touched": result.get("dimensions_touched", []),
            "evidence_type": result.get("evidence_type", "observacion"),
            "emotional_intensity": result.get("emotional_intensity", "media"),
            "key_quotes": result.get("key_quotes", []),
            "context_notes_used": bool(node.get("context_notes")),
            "confidence": float(result.get("confidence", 0.5)),
        }

        saved = _post(base_url, f"/analysis/runs/{run_id}/nodes/{gid}", body)
        results[gid] = saved["id"]
        state["node_analyses"] = results
        state["step"] = 1
        _save_state(state)
        _log(f"  ✓ {node['name']} → node_analysis {saved['id'][:8]}…")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# PASO 2 — Síntesis por grupo
# ─────────────────────────────────────────────────────────────────────────────

def _run_paso2(
    client: OpenAI,
    base_url: str,
    run_id: str,
    input_data: dict,
    node_analyses: dict[str, dict],
    state: dict,
) -> dict[str, str]:
    """Agrupa node_analyses por parent_group_id y sintetiza. Devuelve {group_id: group_analysis_id}."""
    prompt_template = _load_prompt("paso2_grupo.txt")
    results: dict[str, str] = state.get("group_analyses", {})

    nodes = input_data["structure"]["nodes"]
    interviews_by_node = input_data["interviews"]["by_node"]

    # Agrupar nodos por su parent_group_id (o por sí mismos si no tienen parent)
    # Un "grupo" para el Paso 2 es cualquier nodo que tenga hijos, o el nodo mismo.
    # Simplificación: agrupamos por parent_id; los huérfanos forman su propio "grupo de 1"
    groups_map: dict[str, list[dict]] = {}
    for n in nodes:
        pid = n.get("parent_id") or n["id"]
        groups_map.setdefault(pid, []).append(n)

    # También necesitamos los nodos raíz (que tienen hijos) como propios grupos
    parent_ids = {n.get("parent_id") for n in nodes if n.get("parent_id")}
    all_group_ids = set(groups_map.keys()) | parent_ids

    # Construir grupos reales: un grupo = un nodo padre + sus hijos directos
    # Para el análisis, tratamos cada nodo-área como un grupo
    node_map = {n["id"]: n for n in nodes}

    _log(f"Paso 2 — {len(groups_map)} grupos a sintetizar")

    for group_id, member_nodes in groups_map.items():
        if group_id in results:
            grp_name = node_map.get(group_id, {}).get("name", group_id[:8])
            _log(f"  ↷ Grupo '{grp_name}' (ya procesado, skip)")
            continue

        group_node = node_map.get(group_id, {})
        grp_name = group_node.get("name", group_id[:8])

        # Construir node_analyses list para este grupo
        nodes_with_analysis = [
            n for n in member_nodes
            if n["id"] in node_analyses
        ]

        if not nodes_with_analysis:
            _log(f"  ⚠ Grupo '{grp_name}' — sin node_analyses, skip")
            continue

        # Scores cuantitativos del grupo (con std)
        dim_scores_all: dict[str, list[float]] = {}
        for n in member_nodes:
            iv_data = interviews_by_node.get(n["id"], {})
            for dim, stats in iv_data.get("quantitative_scores", {}).items():
                dim_scores_all.setdefault(dim, []).append(stats["score"])

        quantitative_scores = {}
        for dim, vals in dim_scores_all.items():
            avg = sum(vals) / len(vals)
            std = statistics.stdev(vals) if len(vals) > 1 else 0.0
            quantitative_scores[dim] = {"score": round(avg, 3), "std": round(std, 3)}

        # Cobertura del grupo
        completed_in_group = sum(1 for n in member_nodes if n.get("has_interview"))
        coverage = completed_in_group / max(1, len(member_nodes))

        llm_input = {
            "group_name": grp_name,
            "group_area": group_node.get("area", ""),
            "node_analyses": [node_analyses[n["id"]] for n in nodes_with_analysis],
            "quantitative_scores": quantitative_scores,
            "admin_notes": group_node.get("context_notes"),
            "coverage": round(coverage, 3),
        }

        system_prompt = prompt_template.replace("{{input_json}}", json.dumps(llm_input, ensure_ascii=False, indent=2))

        _log(f"  → Grupo '{grp_name}' ({MODEL_PASO2}, {len(nodes_with_analysis)} nodos)…")
        result = _call_llm(client, MODEL_PASO2, system_prompt, "Sintetiza este grupo y devuelve el JSON.")

        body = {
            "run_id": run_id,
            "org_id": input_data["organization"]["id"],
            "group_id": group_id,
            "patterns_internal": result.get("patterns_internal", []),
            "dominant_themes": result.get("dominant_themes", []),
            "tension_level": result.get("tension_level", "medio"),
            "scores_by_dimension": result.get("scores_by_dimension", {}),
            "gap_leader_team": result.get("gap_leader_team"),
            "coverage": round(coverage, 3),
            "confidence": float(result.get("confidence", 0.5)),
        }

        saved = _post(base_url, f"/analysis/runs/{run_id}/groups/{group_id}", body)
        results[group_id] = saved["id"]
        state["group_analyses"] = results
        state["step"] = 2
        _save_state(state)
        _log(f"  ✓ Grupo '{grp_name}' → group_analysis {saved['id'][:8]}…")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# PASO 3 — Análisis organizacional
# ─────────────────────────────────────────────────────────────────────────────

def _run_paso3(
    client: OpenAI,
    base_url: str,
    run_id: str,
    input_data: dict,
    group_analyses: dict[str, dict],
    state: dict,
) -> str:
    """Un único prompt con todos los group_analyses. Devuelve org_analysis_id."""
    if state.get("org_analysis_id"):
        _log("Paso 3 — ya completado, skip")
        return state["org_analysis_id"]

    prompt_template = _load_prompt("paso3_org.txt")
    org = input_data["organization"]
    nodes = input_data["structure"]["nodes"]
    interviews_by_node = input_data["interviews"]["by_node"]

    # Scores globales por dimensión con std
    dim_all: dict[str, list[float]] = {}
    for iv_data in interviews_by_node.values():
        for dim, stats in iv_data.get("quantitative_scores", {}).items():
            dim_all.setdefault(dim, []).append(stats["score"])
    dimension_scores = {
        dim: {
            "score": round(sum(v) / len(v), 3),
            "std": round(statistics.stdev(v) if len(v) > 1 else 0.0, 3),
        }
        for dim, v in dim_all.items()
    }

    llm_input = {
        "org_name": org["name"],
        "org_structure_type": org.get("org_structure_type", "areas"),
        "group_analyses": list(group_analyses.values()),
        "dimension_scores": dimension_scores,
        "network_metrics": input_data.get("network_metrics", {}),
        "document_extractions": input_data.get("documents", []),
        "structure_snapshot": {
            "total_nodes": input_data["structure"]["total_nodes"],
            "total_with_interview": input_data["structure"].get("total_with_interview", 0),
            "org_structure_type": org.get("org_structure_type"),
        },
    }

    system_prompt = prompt_template.replace("{{input_json}}", json.dumps(llm_input, ensure_ascii=False, indent=2))

    _log(f"Paso 3 — análisis organizacional ({MODEL_PASO3})…")
    result = _call_llm(client, MODEL_PASO3, system_prompt, "Analiza la organización completa y devuelve el JSON.")

    body = {
        "run_id": run_id,
        "org_id": org["id"],
        "cross_patterns": result.get("cross_patterns", []),
        "contradictions": result.get("contradictions", []),
        "structural_risks": result.get("structural_risks", []),
        "dimension_scores": dimension_scores,
        "network_metrics": input_data.get("network_metrics", {}),
        "confidence": float(result.get("confidence", 0.5)),
    }

    saved = _post(base_url, f"/analysis/runs/{run_id}/org", body)
    org_analysis_id = saved["id"]
    state["org_analysis_id"] = org_analysis_id
    state["org_analysis"] = result
    state["step"] = 3
    _save_state(state)
    _log(f"✓ org_analysis {org_analysis_id[:8]}…")
    return org_analysis_id


# ─────────────────────────────────────────────────────────────────────────────
# PASO 4 — Síntesis ejecutiva
# ─────────────────────────────────────────────────────────────────────────────

def _run_paso4(
    client: OpenAI,
    base_url: str,
    run_id: str,
    input_data: dict,
    group_analyses: dict[str, dict],
    org_analysis: dict,
    state: dict,
) -> dict:
    """Síntesis final. Devuelve el response de submit_findings."""
    if state.get("step", 0) >= 4 and state.get("diagnosis_id"):
        _log("Paso 4 — ya completado, skip")
        return state.get("paso4_result", {})

    prompt_template = _load_prompt("paso4_sintesis.txt")

    cross_patterns = [p.get("pattern", "") for p in org_analysis.get("cross_patterns", [])]
    contradictions = [
        f"{c.get('formal','')} vs. {c.get('real','')}"
        for c in org_analysis.get("contradictions", [])
    ]
    structural_risks = [r.get("risk", "") for r in org_analysis.get("structural_risks", [])]

    llm_input = {
        "org_analysis": org_analysis,
        "group_analyses": list(group_analyses.values()),
        "top_patterns": cross_patterns[:5],
        "top_contradictions": contradictions[:5],
        "structural_risks": structural_risks[:5],
    }

    system_prompt = prompt_template.replace("{{input_json}}", json.dumps(llm_input, ensure_ascii=False, indent=2))

    _log(f"Paso 4 — síntesis ejecutiva ({MODEL_PASO4})…")
    result = _call_llm(client, MODEL_PASO4, system_prompt, "Produce la síntesis ejecutiva y devuelve el JSON.")

    # Calcular confianza del sistema para cada finding (fórmula MOTOR_ANALISIS.md §4)
    interviews_by_node = input_data["interviews"]["by_node"]
    total_nodes = input_data["structure"]["total_nodes"]
    total_with_iv = input_data["structure"].get("total_with_interview", 0)
    org_coverage = total_with_iv / max(1, total_nodes)

    findings_out = []
    for f in result.get("findings", []):
        node_ids = f.get("node_ids", [])
        # Confianza calculada por sistema (override la del LLM)
        sys_confidence = _compute_confidence(
            pattern_group_count=len(node_ids),
            has_quanti_quali_convergence=bool(f.get("dimensions")),
            coverage=org_coverage,
            only_one_node=len(node_ids) == 1,
        )
        rationale_parts = [f"coverage_org={org_coverage:.0%}"]
        if len(node_ids) > 1:
            rationale_parts.append(f"patrón en {len(node_ids)} nodos (+0.20)")
        if len(node_ids) == 1:
            rationale_parts.append("solo 1 nodo reporta (-0.20)")

        findings_out.append({
            "title": f.get("title", ""),
            "description": f.get("description", ""),
            "type": f.get("type", "observacion"),
            "severity": f.get("severity", "media"),
            "dimensions": f.get("dimensions", []),
            "node_ids": node_ids,
            "confidence": sys_confidence,
            "confidence_rationale": f.get("confidence_rationale") or "; ".join(rationale_parts),
            "evidence_links": f.get("evidence_links", []),
        })

    recs_out = result.get("recommendations", [])

    body = {
        "findings": findings_out,
        "recommendations": recs_out,
        "narrative_md": result.get("narrative_md", ""),
        "executive_summary": result.get("executive_summary", ""),
    }

    saved = _post(base_url, f"/analysis/runs/{run_id}/findings", body)
    state["step"] = 4
    state["diagnosis_id"] = str(saved["diagnosis_id"])
    state["paso4_result"] = saved
    _save_state(state)

    return saved


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline principal
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(org_id: str, base_url: str, resume_run_id: str | None = None) -> None:
    # Validar entorno
    if not OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY no está definida", file=sys.stderr)
        sys.exit(1)
    if not DIAGNOSIS_API_TOKEN:
        print("ERROR: DIAGNOSIS_API_TOKEN no está definida", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=OPENAI_API_KEY)

    # ── Estado (resume o nuevo) ────────────────────────────────────────
    state: dict = {}
    run_id: str

    if resume_run_id:
        state = _load_state(resume_run_id) or {}
        if not state:
            print(f"ERROR: No se encontró estado para run_id={resume_run_id}", file=sys.stderr)
            sys.exit(1)
        run_id = resume_run_id
        _log(f"Resumiendo corrida {run_id} desde paso {state.get('step', 0)}")
    else:
        _log(f"Iniciando nueva corrida para org {org_id}")

    # ── GET input ──────────────────────────────────────────────────────
    _log("Descargando datos de la organización…")
    input_data = _get(base_url, f"/organizations/{org_id}/analysis/input")
    org_name = input_data["organization"]["name"]
    total_nodes = input_data["structure"]["total_nodes"]
    total_iv = input_data["structure"].get("total_with_interview", 0)
    _log(f"Org: {org_name} | {total_nodes} nodos | {total_iv} con entrevista")

    if total_iv == 0:
        print("ERROR: No hay entrevistas completadas. El pipeline necesita al menos una.", file=sys.stderr)
        sys.exit(1)

    # ── Abrir corrida (solo si es nueva) ──────────────────────────────
    if not resume_run_id:
        unique_groups = len({
            n.get("parent_id") or n["id"]
            for n in input_data["structure"]["nodes"]
        })
        resp = _post(base_url, f"/organizations/{org_id}/analysis/runs", {
            "model_used": f"{MODEL_PASO1}/{MODEL_PASO3}",
            "total_nodes": total_iv,
            "total_groups": unique_groups,
        })
        run_id = resp["run_id"]
        state = {
            "run_id": run_id,
            "org_id": org_id,
            "step": 0,
            "node_analyses": {},
            "group_analyses": {},
            "org_analysis_id": None,
        }
        _save_state(state)
        _log(f"Corrida abierta: {run_id}")

    print()

    # ── Paso 1 ────────────────────────────────────────────────────────
    node_analysis_ids = _run_paso1(client, base_url, run_id, input_data, state)
    # Reconstruir objetos para pasar al paso 2
    node_analysis_objs: dict[str, dict] = {}
    for gid, na_id in node_analysis_ids.items():
        node_analysis_objs[gid] = {"id": na_id, "group_id": gid}

    print()

    # ── Paso 2 ────────────────────────────────────────────────────────
    # Para el paso 2 necesitamos pasar los objetos completos de node_analysis
    # Los recuperamos del estado (se guardaron como IDs; construimos objetos mínimos)
    group_analysis_ids = _run_paso2(
        client, base_url, run_id, input_data, node_analysis_objs, state
    )
    group_analysis_objs: dict[str, dict] = {
        gid: {"id": ga_id, "group_id": gid}
        for gid, ga_id in group_analysis_ids.items()
    }

    print()

    # ── Paso 3 ────────────────────────────────────────────────────────
    _run_paso3(client, base_url, run_id, input_data, group_analysis_objs, state)
    org_analysis = state.get("org_analysis", {})

    print()

    # ── Paso 4 ────────────────────────────────────────────────────────
    final = _run_paso4(
        client, base_url, run_id, input_data, group_analysis_objs, org_analysis, state
    )

    print()
    print("═" * 60)
    print(f"  ✓ Pipeline completado")
    print(f"  Org:             {org_name}")
    print(f"  Run ID:          {run_id}")
    print(f"  Diagnosis ID:    {state.get('diagnosis_id', 'n/a')}")
    print(f"  Nodos procesados:{len(node_analysis_ids)}")
    print(f"  Grupos:          {len(group_analysis_ids)}")
    print(f"  Findings:        {final.get('findings_created', '?')}")
    print(f"  Recomendaciones: {final.get('recommendations_created', '?')}")
    print(f"  Status:          {final.get('status', '?')}")
    print("═" * 60)

    # Limpiar archivo de estado al completar exitosamente
    state_file = _state_path(run_id)
    if state_file.exists():
        state_file.unlink()
        _log(f"Estado limpiado: {state_file.name}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Motor de análisis organizacional — pipeline de 4 pasos con OpenAI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Corrida nueva
  python run_analysis.py --org-id 550e8400-e29b-41d4-a716-446655440000

  # Resume tras fallo en paso 3
  python run_analysis.py --org-id 550e8400-e29b-41d4-a716-446655440000 \\
      --resume 7c9e6679-7425-40de-944b-e07fc1f90ae7

  # Backend en otra URL
  python run_analysis.py --org-id <uuid> --base-url https://api.miempresa.com
        """,
    )
    parser.add_argument(
        "--org-id",
        required=True,
        help="UUID de la organización a analizar",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="URL base del backend (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--resume",
        metavar="RUN_ID",
        default=None,
        help="Reanudar una corrida fallida desde su último paso completado",
    )

    args = parser.parse_args()
    run_pipeline(args.org_id, args.base_url, args.resume)


if __name__ == "__main__":
    main()
