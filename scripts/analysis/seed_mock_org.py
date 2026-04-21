#!/usr/bin/env python3
"""
seed_mock_org.py — Constructora Meridian SAS

Crea una organización de prueba completa llamando a los endpoints del backend
via HTTP. NO toca la base de datos directamente.

Prerequisito: docker-compose up -d (backend en localhost:8000)

Uso:
    python seed_mock_org.py
    python seed_mock_org.py --base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_BASE_URL = "http://localhost:8000"

ADMIN_EMAIL    = "admin@meridian.test"
ADMIN_PASSWORD = "MeridianTest2026!"
ADMIN_NAME     = "Admin Meridian"
ORG_NAME       = "Constructora Meridian SAS"

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

class SeedError(Exception):
    pass


def step(msg: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {msg}")
    print(f"{'─'*60}")


def ok(msg: str) -> None:
    print(f"  ✅  {msg}")


def warn(msg: str) -> None:
    print(f"  ⚠️   {msg}", file=sys.stderr)


def fail(msg: str) -> None:
    print(f"  ❌  {msg}", file=sys.stderr)


def post(base: str, path: str, token: str | None, payload: dict) -> dict | None:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{base}{path}"
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        if r.ok:
            return r.json()
        fail(f"POST {path} → {r.status_code}: {r.text[:200]}")
        return None
    except requests.RequestException as e:
        fail(f"POST {path} → connection error: {e}")
        return None


def patch(base: str, path: str, token: str, payload: dict) -> dict | None:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    url = f"{base}{path}"
    try:
        r = requests.patch(url, json=payload, headers=headers, timeout=15)
        if r.ok:
            return r.json()
        fail(f"PATCH {path} → {r.status_code}: {r.text[:200]}")
        return None
    except requests.RequestException as e:
        fail(f"PATCH {path} → connection error: {e}")
        return None


def login_form(base: str, email: str, password: str) -> str | None:
    """Login via OAuth2PasswordRequestForm (form-encoded, not JSON)."""
    url = f"{base}/auth/login"
    try:
        r = requests.post(
            url,
            data={"username": email, "password": password},
            timeout=15,
        )
        if r.ok:
            return r.json().get("access_token")
        fail(f"Login → {r.status_code}: {r.text[:200]}")
        return None
    except requests.RequestException as e:
        fail(f"Login → connection error: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Definición de la org
# ─────────────────────────────────────────────────────────────────────────────

# Nodos: (slug_key, display_name, node_type, parent_key, email, context_notes)
# parent_key = None → raíz
NODES = [
    (
        "ceo",
        "CEO",
        "persona",
        None,
        "ceo@meridian.test",
        "Fundador. Centraliza muchas decisiones. El equipo lo percibe como difícil de acceder. "
        "Empresa en crecimiento acelerado.",
    ),
    (
        "operaciones",
        "Operaciones",
        "area",
        "ceo",
        "",
        "Área con más carga. Procesos no documentados. Alta rotación en los últimos 6 meses.",
    ),
    (
        "gerente_ops",
        "Gerente de Operaciones",
        "persona",
        "operaciones",
        "gerente.ops@meridian.test",
        "8 años en la empresa. Tiene mucho conocimiento pero no lo transfiere. "
        "Cuello de botella frecuente.",
    ),
    (
        "coordinador",
        "Coordinador de Operaciones",
        "persona",
        "operaciones",
        "coordinador@meridian.test",
        "Nuevo (4 meses). Motivado pero sin claridad de rol.",
    ),
    (
        "comercial",
        "Comercial",
        "area",
        "ceo",
        "",
        "El área estrella. Buenos resultados pero poca coordinación con Operaciones.",
    ),
    (
        "director_comercial",
        "Director Comercial",
        "persona",
        "comercial",
        "director.comercial@meridian.test",
        "Muy autónomo. A veces toma decisiones que afectan a Operaciones sin coordinar.",
    ),
    (
        "ejecutivo",
        "Ejecutivo Comercial",
        "persona",
        "comercial",
        "ejecutivo@meridian.test",
        "Talentoso. Siente que no hay criterios claros de ascenso.",
    ),
    (
        "finanzas",
        "Finanzas / CFO",
        "persona",
        "ceo",
        "cfo@meridian.test",
        "Área pequeña. El CFO tiene acceso directo al CEO lo que genera tensión con otros "
        "directores. Las otras áreas no entienden las restricciones financieras. "
        "Toman decisiones sin considerar el impacto en caja.",
    ),
]

# Posiciones aproximadas para el canvas (CEO arriba, árbol hacia abajo)
NODE_POSITIONS: dict[str, tuple[float, float]] = {
    "ceo":              (500.0,  50.0),
    "operaciones":      (200.0, 200.0),
    "gerente_ops":      (100.0, 350.0),
    "coordinador":      (300.0, 350.0),
    "comercial":        (500.0, 200.0),
    "director_comercial":(400.0, 350.0),
    "ejecutivo":        (600.0, 350.0),
    "finanzas":         (800.0, 200.0),
}

# Respuestas de entrevista por nodo
# ────────────────────────────────
# CEO y CFO/Finanzas usan instrumento G (gerente G1-G13).
# El resto usa instrumento E (empleado E1-E10).
#
# single_select → int (índice 0-based de la opción)
# multi_select  → list[int]
# text_open     → str

INTERVIEW_RESPONSES: dict[str, dict] = {
    # ── CEO (instrumento G) ────────────────────────────────────────────────
    "ceo": {
        # G1 centralizacion: "Menos de la mitad" (índice 1) — se autopercibe delegador
        "G1": 1,
        # G2 centralizacion: "Algunas cosas se retrasarían"
        "G2": 1,
        # G3 centralizacion (multi): delegable pero él interviene en descuentos y quejas
        "G3": [0, 1],
        # G4 cuellos_botella (multi): las aprobaciones pasan por él
        "G4": [0],
        # G5 flujo_informacion (multi): tiene dashboards + equipo lo informa
        "G5": [0, 1],
        # G6 incentivos: "Se valora informalmente" — no hay sistema formal de incentivos
        "G6": 1,
        # G7 cultura_error: "Se corrige y se sigue" — pragmático
        "G7": 1,
        # G8 alineacion_estrategica: "Algunos sí, otros no"
        "G8": 1,
        # G9 alineacion (single, mayor riesgo): "Competencia"
        "G9": 0,
        # G10 capacidad_cambio: último intento funcionó
        "G10": 0,
        # G11 visibilidad_financiera: "Sí, con datos concretos"
        "G11": 0,
        # G12 visibilidad: nunca faltó caja
        "G12": 0,
        # G13 texto libre
        "G13": (
            "Creo que el mayor reto es mantener la cultura mientras crecemos tan rápido. "
            "El equipo original conoce los valores, pero los nuevos no los viven de la misma manera."
        ),
    },

    # ── Gerente de Operaciones (instrumento E) ─────────────────────────────
    "gerente_ops": {
        # E1 centralizacion: jefe "Se la pasa apagando incendios" (índice 2)
        "E1": 2,
        # E2 centralizacion: "Se frenaría significativamente" si el jefe se va
        "E2": 3,
        # E3 (multi): pocas decisiones autónomas
        "E3": [0],
        # E4 cuellos_botella (multi): aprobaciones + falta de info
        "E4": [0, 2],
        # E5 flujo_informacion: "Le pregunto a mi jefe o compañero"
        "E5": 1,
        # E6 incentivos: "Se valora informalmente"
        "E6": 1,
        # E7 cultura_error: "Se corrige y no pasa nada"
        "E7": 1,
        # E8 alineacion: "Más o menos"
        "E8": 1,
        # E9 (multi): presión por costos
        "E9": [2],
        # E10 texto libre
        "E10": (
            "Hay muchas cosas que solo yo sé hacer. "
            "Necesitamos documentar mejor los procesos antes de que siga creciendo el equipo."
        ),
    },

    # ── Coordinador (instrumento E) ────────────────────────────────────────
    "coordinador": {
        # E1: jefe apaga incendios
        "E1": 2,
        # E2: operaciones se frenaría
        "E2": 3,
        # E3 (multi): muy pocas decisiones autónomas
        "E3": [0],
        # E4 (multi): aprobaciones + coordinación entre áreas
        "E4": [0, 1],
        # E5: busca la info por su cuenta
        "E5": 2,
        # E6: nadie se da cuenta del esfuerzo
        "E6": 2,
        # E7: le llaman la atención por errores
        "E7": 2,
        # E8: no sabe bien cuál es la estrategia
        "E8": 3,
        # E9 (multi): clientes pidiendo cosas diferentes
        "E9": [0],
        # E10 texto libre
        "E10": (
            "A veces no sé bien cuál es mi alcance de decisión. "
            "Tengo que preguntar por cosas que debería poder resolver solo."
        ),
    },

    # ── Director Comercial (instrumento E) ────────────────────────────────
    "director_comercial": {
        # E1: jefe se enfoca en lo estratégico (alto nivel)
        "E1": 0,
        # E2: todo seguiría normal — muy autónomo
        "E2": 0,
        # E3 (multi): puede tomar muchas decisiones solo
        "E3": [0, 1, 2, 3, 4],
        # E4 (multi): principal cuello: coordinación con otras áreas
        "E4": [1],
        # E5: tiene info disponible en sistema
        "E5": 0,
        # E6: su trabajo es reconocido formalmente
        "E6": 0,
        # E7: errores se analizan para mejorar
        "E7": 0,
        # E8: tiene clara la estrategia
        "E8": 0,
        # E9 (multi): competencia + clientes cambiando
        "E9": [0, 1],
        # E10 texto libre
        "E10": (
            "Operaciones no entiende la velocidad que necesita el negocio. "
            "Perdemos oportunidades por la lentitud interna para ejecutar."
        ),
    },

    # ── Ejecutivo Comercial (instrumento E) ───────────────────────────────
    "ejecutivo": {
        # E1: jefe hace de todo
        "E1": 1,
        # E2: varias cosas quedan paradas
        "E2": 2,
        # E3 (multi): algo de autonomía
        "E3": [1, 2],
        # E4 (multi): coordinación + falta de info
        "E4": [1, 2],
        # E5: pregunta a jefe o compañero
        "E5": 1,
        # E6: nadie se da cuenta del esfuerzo extra
        "E6": 3,
        # E7: le llaman la atención por errores
        "E7": 2,
        # E8: no tiene claro a dónde va la empresa
        "E8": 2,
        # E9 (multi): competencia
        "E9": [0],
        # E10 texto libre
        "E10": (
            "Trabajo duro pero no veo un camino claro de crecimiento aquí. "
            "No hay criterios transparentes de ascenso o reconocimiento."
        ),
    },

    # ── CFO / Finanzas (instrumento G) ────────────────────────────────────
    "finanzas": {
        # G1 centralizacion: "Casi nada" — finanzas no centraliza decisiones ops
        "G1": 0,
        # G2: todo seguiría normal en finanzas
        "G2": 0,
        # G3 (multi): delega decisiones rutinarias
        "G3": [2, 3, 4],
        # G4 (multi): el cuello es la falta de info de otras áreas
        "G4": [2],
        # G5 (multi): tiene dashboards financieros completos
        "G5": [0],
        # G6: reconocimiento formal
        "G6": 0,
        # G7: analiza errores y ajusta proceso
        "G7": 0,
        # G8: equipo de finanzas tiene claro el objetivo
        "G8": 0,
        # G9: tecnología como riesgo principal
        "G9": 2,
        # G10: cambios se sostienen
        "G10": 0,
        # G11: conoce los números exactos
        "G11": 0,
        # G12: tensión presupuestal una o dos veces
        "G12": 1,
        # G13 texto libre
        "G13": (
            "Las otras áreas no entienden las restricciones financieras. "
            "Toman decisiones sin considerar el impacto en caja y después piden explicaciones."
        ),
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def run(base_url: str) -> None:
    base = base_url.rstrip("/")
    created_nodes:   int = 0
    completed_ivs:   int = 0
    failed_steps:    list[str] = []

    node_ids: dict[str, str] = {}   # slug → UUID string

    # ── PASO 1: Registrar usuario admin ──────────────────────────────────────
    step("1/6  Registrar usuario admin")
    reg = post(base, "/auth/register", None, {
        "email":    ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
        "name":     ADMIN_NAME,
        "org_name": ORG_NAME,
    })
    if reg is None:
        warn("Register falló — quizás el usuario ya existe. Intentando login...")
    else:
        ok(f"Usuario creado: {reg['email']} | org_id provisional: {reg.get('organization_id')}")

    # ── PASO 2: Login ─────────────────────────────────────────────────────────
    step("2/6  Login")
    token = login_form(base, ADMIN_EMAIL, ADMIN_PASSWORD)
    if not token:
        fail("No se pudo obtener el token. Abortando.")
        sys.exit(1)
    ok("Token obtenido ✓")

    # ── Obtener org_id del /auth/me ───────────────────────────────────────────
    try:
        me_r = requests.get(
            f"{base}/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        me_data = me_r.json()
        org_id = me_data.get("organization_id")
        if not org_id:
            fail(f"/auth/me no devolvió organization_id: {me_data}")
            sys.exit(1)
        ok(f"org_id: {org_id}")
    except Exception as e:
        fail(f"Error al obtener org_id desde /auth/me: {e}")
        sys.exit(1)

    # ── PASO 3: Actualizar org con datos completos ────────────────────────────
    step("3/6  Actualizar organización con contexto estratégico")
    updated = patch(base, f"/organizations/{org_id}", token, {
        "name":        ORG_NAME,
        "description": (
            "Empresa constructora en fase de crecimiento acelerado. "
            "Proyectos residenciales y comerciales en Colombia."
        ),
        "sector":              "Construcción",
        "org_structure_type":  "mixto",
        "strategic_objectives": (
            "Duplicar la capacidad operativa en los próximos 18 meses manteniendo "
            "los márgenes actuales y la cultura interna."
        ),
        "strategic_concerns": (
            "El conocimiento crítico está concentrado en pocas personas. "
            "La coordinación entre Operaciones y Comercial genera fricciones frecuentes."
        ),
        "key_questions": (
            "¿Cómo documentar y distribuir el conocimiento operativo? "
            "¿Cómo mejorar la coordinación entre áreas sin burocratizar el proceso?"
        ),
        "additional_context": (
            "Empresa fundada hace 12 años. CEO es el fundador y sigue muy involucrado. "
            "Crecimiento del 40% en los últimos 2 años. Equipo de 35 personas."
        ),
    })
    if updated:
        ok(f"Org actualizada: {updated.get('name')}")
    else:
        warn("No se pudo actualizar la org. Continuando...")
        failed_steps.append("actualizar_org")

    # ── PASO 4: Crear nodos ───────────────────────────────────────────────────
    step(f"4/6  Crear {len(NODES)} nodos")

    for slug, name, node_type, parent_slug, email, context_notes in NODES:
        parent_id = node_ids.get(parent_slug) if parent_slug else None
        pos = NODE_POSITIONS.get(slug, (0.0, 0.0))

        payload: dict = {
            "organization_id": org_id,
            "name":            name,
            "node_type":       node_type,
            "email":           email,
            "position_x":      pos[0],
            "position_y":      pos[1],
        }
        if parent_id:
            payload["parent_group_id"] = parent_id

        result = post(base, "/groups", token, payload)
        if not result:
            warn(f"  No se pudo crear nodo '{name}'")
            failed_steps.append(f"crear_nodo_{slug}")
            continue

        nid = str(result["id"])
        node_ids[slug] = nid
        created_nodes += 1
        ok(f"  Nodo creado: {name} ({node_type}) → {nid[:8]}…")

        # Agregar context_notes via PATCH (no está en GroupCreate)
        if context_notes:
            patched = patch(base, f"/groups/{nid}", token, {"context_notes": context_notes})
            if patched:
                ok(f"    └─ context_notes agregado ✓")
            else:
                warn(f"    └─ context_notes falló para {name}")

    # ── PASO 5: Crear miembros e invitaciones ─────────────────────────────────
    step("5/6  Crear miembros y obtener tokens de entrevista")

    # Solo nodos con email tienen entrevistado personal
    respondents = [
        (slug, name, email)
        for slug, name, _, _, email, _ in NODES
        if email
    ]

    interview_tokens: dict[str, str] = {}  # slug → interview_token

    for slug, name, email in respondents:
        nid = node_ids.get(slug)
        if not nid:
            warn(f"  Nodo '{slug}' no fue creado. Saltando miembro.")
            continue

        member = post(base, "/members", token, {
            "organization_id": org_id,
            "name":            name,
            "role_label":      name,
            "group_id":        nid,
        })
        if not member:
            warn(f"  No se pudo crear miembro para {name}")
            failed_steps.append(f"crear_miembro_{slug}")
            continue

        iv_token = member.get("interview_token")
        if iv_token:
            interview_tokens[slug] = iv_token
            ok(f"  {name} → token: {iv_token[:12]}…")
        else:
            warn(f"  Miembro creado pero sin interview_token: {member}")

    # ── PASO 6: Enviar entrevistas ────────────────────────────────────────────
    step("6/6  Enviar respuestas de entrevista")

    for slug, iv_data in INTERVIEW_RESPONSES.items():
        iv_token = interview_tokens.get(slug)
        if not iv_token:
            warn(f"  Sin token para '{slug}'. Saltando entrevista.")
            continue

        result = post(base, f"/entrevista/{iv_token}/submit", None, {"data": iv_data})
        if result:
            ok(f"  {slug} → entrevista enviada ✓ (status: {result.get('token_status')})")
            completed_ivs += 1
        else:
            warn(f"  No se pudo enviar entrevista de '{slug}'")
            failed_steps.append(f"entrevista_{slug}")

    # ── Resumen final ─────────────────────────────────────────────────────────
    print()
    print("═" * 60)
    print("  ✅  SEED COMPLETADO")
    print("═" * 60)
    print(f"  Organización : {ORG_NAME}")
    print(f"  org_id       : {org_id}")
    print(f"  Nodos creados: {created_nodes} / {len(NODES)}")
    print(f"  Entrevistas  : {completed_ivs} / {len(INTERVIEW_RESPONSES)}")
    print(f"  Canvas URL   : http://localhost:3000/org/{org_id}/canvas")

    if failed_steps:
        print()
        print(f"  ⚠️  Pasos con error ({len(failed_steps)}):")
        for s in failed_steps:
            print(f"    – {s}")

    print()
    print("─" * 60)
    print("  Copia esto en tu terminal o en scripts/analysis/.env:")
    print("─" * 60)
    print(f'  export ORG_ID="{org_id}"')
    print(f'  export ADMIN_TOKEN="{token}"')
    print()

    # Guardar en .env.test
    env_path = Path(__file__).parent / ".env.test"
    env_content = (
        f'ORG_ID="{org_id}"\n'
        f'ADMIN_TOKEN="{token}"\n'
        f'DIAGNOSIS_API_TOKEN="{token}"\n'   # alias para run_analysis.py
        f'ADMIN_EMAIL="{ADMIN_EMAIL}"\n'
        f'ADMIN_PASSWORD="{ADMIN_PASSWORD}"\n'
    )
    try:
        env_path.write_text(env_content)
        ok(f"  Valores guardados en {env_path}")
    except OSError as e:
        warn(f"  No se pudo guardar .env.test: {e}")

    print("═" * 60)
    print()


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed Constructora Meridian SAS — org de prueba completa"
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BACKEND_URL", DEFAULT_BASE_URL),
        help=f"URL base del backend (default: {DEFAULT_BASE_URL})",
    )
    args = parser.parse_args()

    run(args.base_url)
