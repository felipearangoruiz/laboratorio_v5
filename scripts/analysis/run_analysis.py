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

Encadenamiento entre pasos (Sprint 4.A — 2026-04-23):
    Cada paso devuelve dos cosas: (a) el id persistido en BD y (b) el
    dict completo del LLM. El dict completo se acumula en memoria local
    (state["node_analyses_full"], state["group_analyses_full"],
    state["org_analysis_full"]) y se inyecta íntegro en el prompt del
    siguiente paso. Antes del Sprint 4.A solo se propagaban los IDs, lo
    que dejaba al Paso 4 operando sobre un resumen filtrado del Paso 3.

    Breaking: los state files pre-Sprint 4.A no son retrocompatibles. Un
    run interrumpido antes del fix debe reiniciarse desde cero.
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

# Sprint 4.B.1 — umbrales para convergencia cuanti+cuali.
#
# Los `dimension_scores` del org_analysis están normalizados a [0, 1] (ver
# _compute_node_scores en backend/app/routers/analysis.py). Un score bajo
# indica debilidad cuantitativa en esa dimensión; un std alto indica
# divergencia entre respondentes. Si el finding toca una dimensión que
# cumple cualquiera de los dos, la señal cualitativa tiene respaldo
# cuantitativo → convergencia.
CONVERGENCE_SCORE_THRESHOLD = 0.50   # score <  umbral → respaldo cuantitativo
CONVERGENCE_STD_THRESHOLD = 0.25     # std   >  umbral → respaldo por dispersión


def _has_quanti_quali_convergence(
    finding_dimensions: list[str],
    dimension_scores: dict[str, dict[str, float]],
) -> bool:
    """True si alguna `dimension` del finding tiene respaldo cuantitativo
    agregado (score bajo o std alto) en el org_analysis.

    Reemplaza el chequeo previo `bool(f.get("dimensions"))` que era un bug:
    solo verificaba que la lista estuviera poblada y por eso aplicaba +0.10
    a casi todos los findings.
    """
    for dim in finding_dimensions:
        stats = dimension_scores.get(dim) or {}
        score = stats.get("score")
        std = stats.get("std")
        if isinstance(score, (int, float)) and score < CONVERGENCE_SCORE_THRESHOLD:
            return True
        if isinstance(std, (int, float)) and std > CONVERGENCE_STD_THRESHOLD:
            return True
    return False


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
) -> tuple[dict[str, str], dict[str, dict]]:
    """Procesa cada nodo con entrevista completada.

    Devuelve:
      - ids:  {node_uuid: node_analysis_id}           (para reanudación y persistencia)
      - full: {node_uuid: dict_completo_del_llm}      (contenidos ricos que el Paso 2
              inyecta íntegros en su prompt; así se cumple el contrato de
              MOTOR_ANALISIS.md §1)
    """
    prompt_template = _load_prompt("paso1_nodo.txt")
    ids: dict[str, str] = state.get("node_analyses", {})
    full: dict[str, dict] = state.get("node_analyses_full", {})

    nodes = input_data["structure"]["nodes"]
    node_map = {n["id"]: n for n in nodes}
    interviews_by_node = input_data["interviews"]["by_node"]
    docs = input_data.get("documents", [])

    nodes_with_data = [n for n in nodes if n.get("has_interview")]
    _log(f"Paso 1 — {len(nodes_with_data)} nodos con entrevista")

    for node in nodes_with_data:
        gid = node["id"]
        if gid in ids and gid in full:
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

        content = {
            "node_id": gid,
            "node_name": node.get("name"),
            "node_role": llm_input["node_role"],
            "node_level": llm_input["node_level"],
            "parent_id": node.get("parent_id"),
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

        body = {
            "run_id": run_id,
            "org_id": input_data["organization"]["id"],
            "node_id": gid,
            "signals_positive": content["signals_positive"],
            "signals_tension": content["signals_tension"],
            "themes": content["themes"],
            "dimensions_touched": content["dimensions_touched"],
            "evidence_type": content["evidence_type"],
            "emotional_intensity": content["emotional_intensity"],
            "key_quotes": content["key_quotes"],
            "context_notes_used": content["context_notes_used"],
            "confidence": content["confidence"],
        }

        saved = _post(base_url, f"/analysis/runs/{run_id}/nodes/{gid}", body)
        ids[gid] = saved["id"]
        content["id"] = saved["id"]
        full[gid] = content
        state["node_analyses"] = ids
        state["node_analyses_full"] = full
        state["step"] = 1
        _save_state(state)
        _log(f"  ✓ {node['name']} → node_analysis {saved['id'][:8]}…")

    # Sanity check: la entrada persistida en BD debe tener contraparte en memoria
    missing = [nid for nid in ids if nid not in full]
    if missing:
        # Este caso solo puede ocurrir si se resume un state file mixto
        # (parcialmente pre-4.A). _load_state ya aborta antes, pero defensivo.
        raise APIError(
            f"Inconsistencia en state: {len(missing)} node_analyses sin contenido. "
            f"Reinicia el run desde cero."
        )

    return ids, full


# ─────────────────────────────────────────────────────────────────────────────
# PASO 2 — Síntesis por grupo
# ─────────────────────────────────────────────────────────────────────────────

def _run_paso2(
    client: OpenAI,
    base_url: str,
    run_id: str,
    input_data: dict,
    node_analyses_full: dict[str, dict],
    state: dict,
) -> tuple[dict[str, str], dict[str, dict]]:
    """Sintetiza cada grupo inyectando los node_analyses completos del Paso 1.

    Devuelve:
      - ids:  {group_uuid: group_analysis_id}
      - full: {group_uuid: dict_completo_del_llm}    (inyectado íntegro al Paso 3)
    """
    prompt_template = _load_prompt("paso2_grupo.txt")
    ids: dict[str, str] = state.get("group_analyses", {})
    full: dict[str, dict] = state.get("group_analyses_full", {})

    nodes = input_data["structure"]["nodes"]
    interviews_by_node = input_data["interviews"]["by_node"]

    # Agrupar nodos por su parent_id (o por sí mismos si no tienen parent)
    groups_map: dict[str, list[dict]] = {}
    for n in nodes:
        pid = n.get("parent_id") or n["id"]
        groups_map.setdefault(pid, []).append(n)

    node_map = {n["id"]: n for n in nodes}

    _log(f"Paso 2 — {len(groups_map)} grupos a sintetizar")

    for group_id, member_nodes in groups_map.items():
        grp_name = node_map.get(group_id, {}).get("name", group_id[:8])

        if group_id in ids and group_id in full:
            _log(f"  ↷ Grupo '{grp_name}' (ya procesado, skip)")
            continue

        group_node = node_map.get(group_id, {})

        nodes_with_analysis = [
            n for n in member_nodes
            if n["id"] in node_analyses_full
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

        # Sprint 4.B.1: size = número de respondentes del grupo con node_analysis.
        # Los grupos size=1 no pueden sostener patrones internos (un patrón
        # requiere repetición o divergencia entre al menos dos voces).
        size = len(nodes_with_analysis)

        llm_input = {
            "group_name": grp_name,
            "group_area": group_node.get("area", ""),
            "size": size,
            # Inyectamos los dicts completos del Paso 1 (no solo IDs).
            "node_analyses": [node_analyses_full[n["id"]] for n in nodes_with_analysis],
            "quantitative_scores": quantitative_scores,
            "admin_notes": group_node.get("context_notes"),
            "coverage": round(coverage, 3),
        }

        system_prompt = prompt_template.replace("{{input_json}}", json.dumps(llm_input, ensure_ascii=False, indent=2))

        _log(f"  → Grupo '{grp_name}' ({MODEL_PASO2}, {len(nodes_with_analysis)} nodos)…")
        result = _call_llm(client, MODEL_PASO2, system_prompt, "Sintetiza este grupo y devuelve el JSON.")

        # Defensa en profundidad: el prompt instruye que size=1 → patterns_internal=[],
        # pero el código lo fuerza aunque el LLM lo devuelva poblado.
        if size == 1:
            patterns_internal = []
        else:
            patterns_internal = result.get("patterns_internal", [])

        content = {
            "group_id": group_id,
            "group_name": grp_name,
            "group_area": group_node.get("area", ""),
            "size": size,
            "patterns_internal": patterns_internal,
            "dominant_themes": result.get("dominant_themes", []),
            "tension_level": result.get("tension_level", "medio"),
            "scores_by_dimension": result.get("scores_by_dimension", {}),
            "gap_leader_team": result.get("gap_leader_team"),
            "quantitative_scores": quantitative_scores,
            "coverage": round(coverage, 3),
            "member_node_ids": [n["id"] for n in nodes_with_analysis],
            "confidence": float(result.get("confidence", 0.5)),
        }

        body = {
            "run_id": run_id,
            "org_id": input_data["organization"]["id"],
            "node_id": group_id,
            "patterns_internal": content["patterns_internal"],
            "dominant_themes": content["dominant_themes"],
            "tension_level": content["tension_level"],
            "scores_by_dimension": content["scores_by_dimension"],
            "gap_leader_team": content["gap_leader_team"],
            "coverage": content["coverage"],
            "confidence": content["confidence"],
        }

        saved = _post(base_url, f"/analysis/runs/{run_id}/groups/{group_id}", body)
        ids[group_id] = saved["id"]
        content["id"] = saved["id"]
        full[group_id] = content
        state["group_analyses"] = ids
        state["group_analyses_full"] = full
        state["step"] = 2
        _save_state(state)
        _log(f"  ✓ Grupo '{grp_name}' → group_analysis {saved['id'][:8]}…")

    missing = [gid for gid in ids if gid not in full]
    if missing:
        raise APIError(
            f"Inconsistencia en state: {len(missing)} group_analyses sin contenido. "
            f"Reinicia el run desde cero."
        )

    return ids, full


# ─────────────────────────────────────────────────────────────────────────────
# PASO 3 — Análisis organizacional
# ─────────────────────────────────────────────────────────────────────────────

def _run_paso3(
    client: OpenAI,
    base_url: str,
    run_id: str,
    input_data: dict,
    group_analyses_full: dict[str, dict],
    state: dict,
) -> tuple[str, dict]:
    """Un único prompt con todos los group_analyses completos.

    Devuelve (org_analysis_id, dict_completo_del_llm) para que el Paso 4
    pueda inyectar el contenido íntegro.
    """
    if state.get("org_analysis_id") and state.get("org_analysis_full"):
        _log("Paso 3 — ya completado, skip")
        return state["org_analysis_id"], state["org_analysis_full"]

    prompt_template = _load_prompt("paso3_org.txt")
    org = input_data["organization"]
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
        # Inyectamos los dicts completos del Paso 2 (no solo IDs).
        "group_analyses": list(group_analyses_full.values()),
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
    # Guardamos el dict completo + dimension_scores calculados por el motor,
    # para que el Paso 4 tenga la foto completa en un solo objeto.
    full = dict(result)
    full["id"] = org_analysis_id
    full["dimension_scores"] = dimension_scores
    full["network_metrics"] = input_data.get("network_metrics", {})
    state["org_analysis_id"] = org_analysis_id
    state["org_analysis_full"] = full
    state["step"] = 3
    _save_state(state)
    _log(f"✓ org_analysis {org_analysis_id[:8]}…")
    return org_analysis_id, full


# ─────────────────────────────────────────────────────────────────────────────
# PASO 4 — Síntesis ejecutiva
# ─────────────────────────────────────────────────────────────────────────────

def _run_paso4(
    client: OpenAI,
    base_url: str,
    run_id: str,
    input_data: dict,
    node_analyses_full: dict[str, dict],
    group_analyses_full: dict[str, dict],
    org_analysis_full: dict,
    state: dict,
) -> dict:
    """Síntesis final. Devuelve el response de submit_findings.

    Recibe node_analyses_full, group_analyses_full y org_analysis_full
    íntegros. Sprint 4.B Ronda 2: los node_analyses ahora llegan al input
    del Paso 4 para que el LLM pueda citar key_quotes textuales y fundar
    evidence_links con node_analysis_id concreto.
    """
    if state.get("step", 0) >= 4 and state.get("diagnosis_id"):
        _log("Paso 4 — ya completado, skip")
        return state.get("paso4_result", {})

    prompt_template = _load_prompt("paso4_sintesis.txt")

    cross_patterns = [p.get("pattern", "") for p in org_analysis_full.get("cross_patterns", [])]
    contradictions = [
        f"{c.get('formal','')} vs. {c.get('real','')}"
        for c in org_analysis_full.get("contradictions", [])
    ]
    structural_risks = [r.get("risk", "") for r in org_analysis_full.get("structural_risks", [])]

    llm_input = {
        "org_analysis": org_analysis_full,
        "group_analyses": list(group_analyses_full.values()),
        # Sprint 4.B Ronda 2 — node_analyses completos para fundar citas
        # textuales y evidence_links a nivel de respondente individual.
        "node_analyses": list(node_analyses_full.values()),
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
    # Sprint 4.B.1 — scores agregados del org_analysis para chequear
    # convergencia cuanti+cuali real (antes era `bool(f.get("dimensions"))`,
    # que siempre daba True si había dimensiones).
    org_dimension_scores = org_analysis_full.get("dimension_scores", {}) or {}

    findings_out = []
    for f in result.get("findings", []):
        node_ids = f.get("node_ids", [])
        # Confianza calculada por sistema (override la del LLM)
        sys_confidence = _compute_confidence(
            pattern_group_count=len(node_ids),
            has_quanti_quali_convergence=_has_quanti_quali_convergence(
                f.get("dimensions", []), org_dimension_scores,
            ),
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
        # Sprint 4.A — los state files pre-Sprint 4.A solo persistían IDs
        # (sin los contenidos completos que el encadenamiento actual
        # necesita). No hay forma segura de reanudar: el Paso 2 requiere
        # ver los node_analyses del Paso 1 íntegros, y el único sitio donde
        # viven sin una consulta nueva a BD es el state file.
        has_step1_done = state.get("step", 0) >= 1 and state.get("node_analyses")
        has_step2_done = state.get("step", 0) >= 2 and state.get("group_analyses")
        missing_full_step1 = has_step1_done and not state.get("node_analyses_full")
        missing_full_step2 = has_step2_done and not state.get("group_analyses_full")
        if missing_full_step1 or missing_full_step2:
            print(
                "ERROR: state file con formato pre-Sprint 4.A detectado "
                "(solo contiene IDs, sin los contenidos de pasos anteriores). "
                "Reiniciar el run desde cero — no es retrocompatible.",
                file=sys.stderr,
            )
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
            "node_analyses_full": {},
            "group_analyses": {},
            "group_analyses_full": {},
            "org_analysis_id": None,
            "org_analysis_full": None,
        }
        _save_state(state)
        _log(f"Corrida abierta: {run_id}")

    print()

    # ── Paso 1 ────────────────────────────────────────────────────────
    node_analysis_ids, node_analyses_full = _run_paso1(
        client, base_url, run_id, input_data, state
    )

    print()

    # ── Paso 2 ────────────────────────────────────────────────────────
    # Inyecta node_analyses completos (no IDs).
    group_analysis_ids, group_analyses_full = _run_paso2(
        client, base_url, run_id, input_data, node_analyses_full, state
    )

    print()

    # ── Paso 3 ────────────────────────────────────────────────────────
    # Inyecta group_analyses completos (no IDs).
    _, org_analysis_full = _run_paso3(
        client, base_url, run_id, input_data, group_analyses_full, state
    )

    print()

    # ── Paso 4 ────────────────────────────────────────────────────────
    # Inyecta group_analyses_full y org_analysis_full íntegros.
    final = _run_paso4(
        client, base_url, run_id, input_data,
        node_analyses_full, group_analyses_full, org_analysis_full, state,
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
