#!/usr/bin/env python3
"""Crea una organización de prueba realista con datos completos para el motor de análisis.

Qué crea:
  - Org: "Empresa Demo SAS" (tipo mixto)
  - 8 nodos: 1 CEO, 3 directores, 4 areas/personas con context_notes
  - 6 entrevistas completadas (mix de tensiones y fortalezas)
  - 2 documentos mock (misión/visión, organigrama)

Uso:
    cd scripts/analysis
    python mock/seed_mock_org.py [--base-url http://localhost:8000]

Variables de entorno (o en .env):
    SEED_ADMIN_EMAIL     (default: demo@empresa.com)
    SEED_ADMIN_PASSWORD  (default: Demo1234!)

El script imprime al final:
    org_id = <uuid>
    token  = <jwt>
Guárdalos para el .env del run_analysis.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = os.environ.get("SEED_ADMIN_EMAIL", "demo@empresa.com")
ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD", "Demo1234!")


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _post(path: str, body: dict, token: str | None = None) -> Any:
    headers = _h(token) if token else {"Content-Type": "application/json"}
    r = requests.post(f"{BASE_URL}{path}", headers=headers, json=body, timeout=30)
    if not r.ok:
        print(f"  ERR POST {path}: {r.status_code} {r.text[:200]}", file=sys.stderr)
        r.raise_for_status()
    return r.json()


def _patch(path: str, body: dict, token: str) -> Any:
    r = requests.patch(f"{BASE_URL}{path}", headers=_h(token), json=body, timeout=30)
    if not r.ok:
        print(f"  ERR PATCH {path}: {r.status_code} {r.text[:200]}", file=sys.stderr)
        r.raise_for_status()
    return r.json()


def _get(path: str, token: str) -> Any:
    r = requests.get(f"{BASE_URL}{path}", headers=_h(token), timeout=30)
    r.raise_for_status()
    return r.json()


def log(msg: str) -> None:
    print(f"[seed] {msg}", flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Auth — registrar o loguear
# ─────────────────────────────────────────────────────────────────────────────

def setup_auth() -> tuple[str, str]:
    """Registra (o loguea si ya existe) el admin. Devuelve (token, org_id)."""
    try:
        resp = _post("/auth/register", {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "name": "Admin Demo",
            "org_name": "Empresa Demo SAS",
        })
        token = resp["access_token"]
        org_id = resp["organization_id"]
        log(f"Usuario creado: {ADMIN_EMAIL}")
    except requests.HTTPError as e:
        if "409" in str(e) or "already" in str(e).lower():
            log(f"Usuario ya existe, logueando…")
            resp = _post("/auth/login", {
                "username": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
            })
            token = resp["access_token"]
            orgs = _get("/organizations", token)
            org_id = orgs[0]["id"] if orgs else None
            if not org_id:
                raise RuntimeError("No se encontró org para el usuario existente")
        else:
            raise

    return token, org_id


# ─────────────────────────────────────────────────────────────────────────────
# 2. Actualizar org con contexto real
# ─────────────────────────────────────────────────────────────────────────────

def update_org(token: str, org_id: str) -> None:
    _patch(f"/organizations/{org_id}", {
        "description": "Empresa de consultoría y servicios tecnológicos con 12 años de trayectoria. "
                       "Opera en tres verticales: consultoría estratégica, desarrollo de software y capacitación.",
        "sector": "Servicios tecnológicos",
        "org_structure_type": "mixto",
        "strategic_objectives": "Duplicar el revenue de consultoría en 18 meses manteniendo la calidad del equipo actual. "
                                 "Expandir el área de capacitación al mercado regional.",
        "strategic_concerns": "Alta rotación en el equipo de desarrollo. "
                               "Dependencia excesiva de 2-3 clientes grandes. "
                               "Proceso de toma de decisiones muy centralizado en la dirección general.",
        "key_questions": "¿Cómo distribuimos mejor la autoridad sin perder coherencia? "
                         "¿Qué está impidiendo que los directores tomen decisiones con más autonomía?",
        "additional_context": "La empresa pasó por una reestructuración hace 8 meses. "
                               "Hay mucha incertidumbre sobre los nuevos roles y responsabilidades.",
    }, token)
    log("Org actualizada con contexto estratégico")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Crear nodos con jerarquía real
# ─────────────────────────────────────────────────────────────────────────────

def create_nodes(token: str, org_id: str) -> dict[str, str]:
    """Crea 8 nodos y devuelve {nombre_clave: group_id}."""
    nodes: dict[str, str] = {}

    # ── Nivel 0: CEO ───────────────────────────────────────────────────
    ceo = _post("/groups", {
        "organization_id": org_id,
        "node_type": "persona",
        "name": "Dirección General",
        "tarea_general": "CEO",
        "area": "Dirección",
        "nivel_jerarquico": 0,
        "tipo_nivel": "liderazgo",
        "email": "ceo@empresa-demo.com",
        "position_x": 400.0,
        "position_y": 50.0,
    }, token)
    nodes["ceo"] = ceo["id"]
    log(f"  Nodo: Dirección General (CEO) → {ceo['id'][:8]}…")

    # ── Nivel 1: Directores ────────────────────────────────────────────
    dir_ops = _post("/groups", {
        "organization_id": org_id,
        "node_type": "persona",
        "name": "Dirección de Operaciones",
        "tarea_general": "Director de Operaciones",
        "area": "Operaciones",
        "nivel_jerarquico": 1,
        "tipo_nivel": "dirección",
        "parent_group_id": nodes["ceo"],
        "email": "ops@empresa-demo.com",
        "position_x": 150.0,
        "position_y": 200.0,
    }, token)
    nodes["dir_ops"] = dir_ops["id"]
    log(f"  Nodo: Dir. Operaciones → {dir_ops['id'][:8]}…")

    dir_tech = _post("/groups", {
        "organization_id": org_id,
        "node_type": "persona",
        "name": "Dirección de Tecnología",
        "tarea_general": "Director de Tecnología",
        "area": "Tecnología",
        "nivel_jerarquico": 1,
        "tipo_nivel": "dirección",
        "parent_group_id": nodes["ceo"],
        "email": "tech@empresa-demo.com",
        "position_x": 400.0,
        "position_y": 200.0,
    }, token)
    nodes["dir_tech"] = dir_tech["id"]
    log(f"  Nodo: Dir. Tecnología → {dir_tech['id'][:8]}…")

    dir_cap = _post("/groups", {
        "organization_id": org_id,
        "node_type": "persona",
        "name": "Dirección de Capacitación",
        "tarea_general": "Director de Capacitación",
        "area": "Capacitación",
        "nivel_jerarquico": 1,
        "tipo_nivel": "dirección",
        "parent_group_id": nodes["ceo"],
        "email": "cap@empresa-demo.com",
        "position_x": 650.0,
        "position_y": 200.0,
    }, token)
    nodes["dir_cap"] = dir_cap["id"]
    log(f"  Nodo: Dir. Capacitación → {dir_cap['id'][:8]}…")

    # ── Nivel 2: Equipos ───────────────────────────────────────────────
    equipo_dev = _post("/groups", {
        "organization_id": org_id,
        "node_type": "area",
        "name": "Equipo de Desarrollo",
        "tarea_general": "Desarrollo de software para clientes",
        "area": "Tecnología",
        "nivel_jerarquico": 2,
        "tipo_nivel": "equipo",
        "parent_group_id": nodes["dir_tech"],
        "email": "dev@empresa-demo.com",
        "position_x": 300.0,
        "position_y": 380.0,
    }, token)
    nodes["equipo_dev"] = equipo_dev["id"]
    log(f"  Nodo: Equipo Desarrollo → {equipo_dev['id'][:8]}…")

    equipo_consulta = _post("/groups", {
        "organization_id": org_id,
        "node_type": "area",
        "name": "Equipo de Consultoría",
        "tarea_general": "Consultoría estratégica y diagnóstico organizacional",
        "area": "Operaciones",
        "nivel_jerarquico": 2,
        "tipo_nivel": "equipo",
        "parent_group_id": nodes["dir_ops"],
        "email": "consulta@empresa-demo.com",
        "position_x": 80.0,
        "position_y": 380.0,
    }, token)
    nodes["equipo_consulta"] = equipo_consulta["id"]
    log(f"  Nodo: Equipo Consultoría → {equipo_consulta['id'][:8]}…")

    equipo_admin = _post("/groups", {
        "organization_id": org_id,
        "node_type": "area",
        "name": "Administración y Finanzas",
        "tarea_general": "Gestión contable, nómina, compras y presupuesto",
        "area": "Operaciones",
        "nivel_jerarquico": 2,
        "tipo_nivel": "equipo",
        "parent_group_id": nodes["dir_ops"],
        "email": "admin@empresa-demo.com",
        "position_x": 200.0,
        "position_y": 380.0,
    }, token)
    nodes["equipo_admin"] = equipo_admin["id"]
    log(f"  Nodo: Adm. y Finanzas → {equipo_admin['id'][:8]}…")

    equipo_cap = _post("/groups", {
        "organization_id": org_id,
        "node_type": "area",
        "name": "Equipo de Capacitación",
        "tarea_general": "Diseño y dictado de programas de formación corporativa",
        "area": "Capacitación",
        "nivel_jerarquico": 2,
        "tipo_nivel": "equipo",
        "parent_group_id": nodes["dir_cap"],
        "email": "formacion@empresa-demo.com",
        "position_x": 600.0,
        "position_y": 380.0,
    }, token)
    nodes["equipo_cap"] = equipo_cap["id"]
    log(f"  Nodo: Equipo Capacitación → {equipo_cap['id'][:8]}…")

    # ── Agregar context_notes realistas ────────────────────────────────
    context_notes = {
        "ceo": "Lleva 3 años como CEO. Fundadora de la empresa. Tendencia a involucrarse en decisiones "
               "operativas. Ha manifestado querer delegar más pero le cuesta soltar el control.",
        "dir_ops": "Ingresó hace 1 año tras la reestructuración. Siente que su rol no está bien definido. "
                   "Hay fricción con la dirección general sobre qué decisiones puede tomar.",
        "dir_tech": "El más senior del equipo técnico. Muy respetado por el equipo de desarrollo. "
                    "Reporta sentir que no tiene suficiente información financiera para planificar bien.",
        "dir_cap": "Nuevo en el rol. Antes era formador senior. Tiene ideas claras sobre el negocio "
                   "pero poca experiencia gestionando personas. Su equipo lo valora pero le falta estructura.",
        "equipo_dev": "Equipo de 5 personas. Alta rotación en el último año (2 salidas). "
                      "Mucha presión de entrega. Varios miembros reportan privadamente agotamiento.",
        "equipo_consulta": "Equipo pequeño (3 personas). Muy autónomo. Trabaja muy bien. "
                           "Riesgo: dependencia alta en una sola persona que lleva todos los clientes clave.",
        "equipo_admin": "Una sola persona full-time + apoyo externo. Sobrecargada. "
                        "No tiene visibilidad del presupuesto real: trabaja con la información que le pasan.",
        "equipo_cap": "Equipo de 4 formadores. Motivados pero sienten que la empresa no invierte en su desarrollo. "
                      "Hay mucha incertidumbre sobre si el área va a crecer o se va a reducir.",
    }
    for key, notes in context_notes.items():
        _patch(f"/groups/{nodes[key]}", {"context_notes": notes}, token)

    log("Context notes agregadas a todos los nodos")
    return nodes


# ─────────────────────────────────────────────────────────────────────────────
# 4. Crear miembros y entrevistas
# ─────────────────────────────────────────────────────────────────────────────

# Respuestas realistas usando question IDs del instrumento v2
# G1-G13: preguntas de gerente | E1-E10: preguntas de empleado
# Valores son índices 0-based en las opciones de cada pregunta.

INTERVIEW_DATA = {
    # CEO — responde como gerente (G1-G13)
    # Señales de centralización alta + buena visión estratégica
    "ceo": {
        "G1": 3,          # "La mayor parte" del tiempo en operaciones del día a día
        "G2": 0,          # Si se fuera una semana, "todo seguiría normal" — centralización oculta
        "G3": ["Definir prioridades", "Aprobar presupuestos", "Revisar entregas a clientes"],
        "G4": 2,          # "Más o menos la mitad" de decisiones podría tomar otra persona
        "G5": ["Reuniones directas", "Mensajes de WhatsApp/Slack"],  # NO reportes/dashboards
        "G6": 4,          # "No sé cómo lo percibe mi equipo" — incentivos ciegos
        "G7": 3,          # "Me entero tarde" de los errores
        "G8": 1,          # Comunicación "algo difícil"
        "G9": 2,          # Alineación estratégica "más o menos"
        "G10": 1,         # Capacidad de cambio "baja"
        "G11": 2,         # Visibilidad financiera: "No lo sé con certeza"
        "G12": 2,         # Restricciones financieras llegan al equipo: "Varias veces"
        "G13": 1,         # Cultura de error: "A veces se penaliza"
        # Preguntas abiertas
        "_open_1": "Siento que el equipo necesita más autonomía pero cuando delego las cosas no salen como yo espero. No sé si es un problema de habilidades o de comunicación.",
        "_open_2": "Lo más crítico ahora mismo es que dependemos demasiado de pocos clientes y de pocas personas. Si se va alguien clave, nos quedamos sin capacidad.",
    },

    # Director de Operaciones — como gerente/empleado mixto
    "dir_ops": {
        "G1": 2,          # Mitad del tiempo en operaciones
        "G2": 2,          # Si se fuera: "Algunas cosas se atracarían"
        "G3": ["Coordinar con clientes", "Revisar entregas"],
        "G4": 3,          # La mayoría de decisiones podría tomar otra persona
        "G5": ["Reuniones directas", "Email"],
        "G6": 2,          # "Creo que lo valoran pero no estoy seguro"
        "G7": 2,          # "Me entero cuando ya es un problema"
        "G8": 2,          # Comunicación regular
        "G9": 1,          # Alineación baja
        "G10": 2,         # Capacidad de cambio media
        "G11": 1,         # Visibilidad financiera limitada
        "G12": 1,         # Restricciones llegan poco
        "G13": 2,         # Cultura de error neutral
        "_open_1": "Mi rol no está bien definido desde la reestructuración. A veces siento que me meto en cosas que no son mías porque si no, nadie las hace.",
        "_open_2": "Hay decisiones que podría tomar yo solo pero siempre tengo que escalar a la dirección general. Eso frena mucho el ritmo.",
    },

    # Director de Tecnología — frustración con falta de info financiera
    "dir_tech": {
        "G1": 1,          # Poco tiempo en operaciones day-to-day
        "G2": 3,          # Si se fuera: "Se atracaría bastante"
        "G3": ["Arquitectura técnica", "Decisiones de stack", "Revisión de código crítico"],
        "G4": 1,          # Pocas decisiones podría delegar
        "G5": ["Reuniones directas", "Herramientas técnicas (Jira, GitHub)"],
        "G6": 1,          # "Creo que sí valoran el trabajo técnico"
        "G7": 1,          # "Me entero rápido"
        "G8": 1,          # Comunicación buena dentro de tech
        "G9": 2,          # Alineación media
        "G10": 1,         # Buena capacidad de cambio en tech
        "G11": 2,         # "No tengo visibilidad del presupuesto real"
        "G12": 2,         # Restricciones sí llegan
        "G13": 1,         # Cultura de error ok
        "_open_1": "El equipo de desarrollo está agotado. Llevamos 6 meses con entregas continuas sin tiempo para refactorizar o aprender cosas nuevas.",
        "_open_2": "No sé cuánto presupuesto tengo para el año. Me enteré de recortes por terceros, no por la dirección directamente.",
    },

    # Equipo de Desarrollo — alta tensión, agotamiento
    "equipo_dev": {
        "E1": 4,          # Autonomía: "Casi nunca puedo decidir cómo hago mi trabajo"
        "E2": 3,          # Información: "A veces no sé qué está pasando"
        "E3": 3,          # Reconocimiento: "Rara vez me reconocen"
        "E4": [
            "La carga de trabajo es desigual",
            "Hay dependencias que bloquean mi trabajo",
        ],
        "E5": 4,          # Cuellos de botella: "Muy seguido"
        "E6": 3,          # Comunicación hacia arriba: difícil
        "E7": 2,          # Cultura de error: "A veces hay consecuencias negativas"
        "E8": 1,          # Alineación: "Más o menos sé hacia dónde va la empresa"
        "E9": 3,          # Cambio: "Los cambios nos caen de sorpresa"
        "E10": 4,         # Visibilidad financiera: "No sé nada de las finanzas"
        "_open_1": "Estamos entregando todo a tiempo pero a un costo enorme para el equipo. Nadie pregunta cómo estamos, solo si la entrega va a salir.",
        "_open_2": "Dos personas que se fueron el año pasado dejaron sin documentar partes críticas del sistema. Ahora todo depende de dos personas y nadie lo ve como un riesgo.",
    },

    # Equipo de Consultoría — mayormente positivo, riesgo de dependencia
    "equipo_consulta": {
        "E1": 2,          # Autonomía: "Tengo bastante autonomía"
        "E2": 2,          # Información: "Generalmente sé lo que necesito"
        "E3": 2,          # Reconocimiento: "A veces me reconocen"
        "E4": ["La comunicación entre áreas podría mejorar"],
        "E5": 2,          # Cuellos de botella: "A veces"
        "E6": 2,          # Comunicación hacia arriba: ok
        "E7": 1,          # Cultura de error: "Generalmente se ve como aprendizaje"
        "E8": 2,          # Alineación: "Sé hacia dónde vamos"
        "E9": 2,          # Cambio: "Nos avisan con algo de tiempo"
        "E10": 3,         # Visibilidad financiera: "Solo lo básico"
        "_open_1": "Me gusta mucho mi trabajo y tengo libertad para hacerlo bien. Mi preocupación es que si yo me voy, no hay nadie que pueda tomar mis clientes.",
        "_open_2": "Sería bueno que la empresa invirtiera en formarnos en metodologías nuevas. Vamos quedando atrás comparado con competidores.",
    },

    # Administración — sobrecarga, falta de info
    "equipo_admin": {
        "E1": 3,          # Poca autonomía en decisiones financieras
        "E2": 4,          # "Casi nunca tengo la información que necesito"
        "E3": 3,          # Poco reconocimiento
        "E4": [
            "La carga de trabajo es desigual",
            "No tengo los recursos para hacer bien mi trabajo",
        ],
        "E5": 4,          # Muchos cuellos de botella
        "E6": 3,          # Comunicación difícil
        "E7": 3,          # Cultura de error negativa
        "E8": 1,          # Algo de alineación estratégica
        "E9": 4,          # Los cambios llegan de sorpresa
        "E10": 2,         # Algo de visibilidad financiera
        "_open_1": "Manejo la contabilidad y la nómina de toda la empresa pero no sé cuál es el presupuesto del año. Me pasan las facturas para pagar y ya. No puedo planificar nada.",
        "_open_2": "Soy la única persona full-time en administración. Cuando hay picos de trabajo (cierre de año, auditorías) simplemente no alcanza.",
    },
}


def create_members_and_interviews(token: str, org_id: str, nodes: dict[str, str]) -> None:
    """Crea miembros y simula la entrega de sus entrevistas."""

    # Nodos que tendrán entrevista (6 de 8 — coverage ~75%)
    interview_nodes = ["ceo", "dir_ops", "dir_tech", "equipo_dev", "equipo_consulta", "equipo_admin"]
    # Sin entrevista: dir_cap, equipo_cap (cobertura incompleta, como pide el spec)

    for node_key in interview_nodes:
        gid = nodes[node_key]
        data = INTERVIEW_DATA[node_key]

        # Separar preguntas abiertas de las cerradas
        interview_data = {k: v for k, v in data.items() if not k.startswith("_open")}

        # Crear miembro
        member = _post("/members", {
            "organization_id": org_id,
            "group_id": gid,
            "name": f"Respondente {node_key.replace('_', ' ').title()}",
            "role_label": _role_label(node_key),
        }, token)
        member_token = member["interview_token"]
        log(f"  Miembro: {node_key} → token {member_token[:8]}…")

        # Activar la entrevista (GET primero para cambiar a in_progress)
        requests.get(f"{BASE_URL}/entrevista/{member_token}", timeout=10)

        # Enviar entrevista completada
        _post(f"/entrevista/{member_token}/submit", {"data": interview_data})
        log(f"  ✓ Entrevista completada: {node_key}")
        time.sleep(0.3)  # pequeño delay para no saturar


def _role_label(node_key: str) -> str:
    labels = {
        "ceo": "CEO / Directora General",
        "dir_ops": "Director de Operaciones",
        "dir_tech": "Director de Tecnología",
        "dir_cap": "Director de Capacitación",
        "equipo_dev": "Líder de Desarrollo",
        "equipo_consulta": "Consultor Senior",
        "equipo_admin": "Coordinadora Administrativa",
        "equipo_cap": "Formador Senior",
    }
    return labels.get(node_key, node_key)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Crear documentos mock (archivos de texto simulados)
# ─────────────────────────────────────────────────────────────────────────────

def create_mock_documents(token: str, org_id: str) -> None:
    """Crea 2 documentos institucionales mock via API."""
    # La API de documentos sube archivos reales; para el mock,
    # creamos archivos temporales de texto y los subimos.
    import tempfile
    import os

    docs_to_create = [
        {
            "label": "Misión, Visión y Valores",
            "doc_type": "institutional",
            "content": """EMPRESA DEMO SAS — Misión, Visión y Valores

MISIÓN
Potenciar el crecimiento de organizaciones a través de consultoría estratégica,
soluciones tecnológicas y programas de formación de alta calidad.

VISIÓN
Ser la firma de referencia en transformación organizacional en América Latina para 2027.

VALORES
- Excelencia técnica: no entregamos nada que no funcione bien
- Autonomía responsable: cada persona es dueña de sus compromisos
- Aprendizaje continuo: los errores son datos, no fracasos
- Transparencia: la información fluye abiertamente en todos los niveles
- Compromiso con el cliente: su éxito es nuestro éxito

NOTA INTERNA (Comité de Dirección, marzo 2026):
Se ha detectado una brecha entre los valores declarados (especialmente autonomía y
transparencia) y las prácticas cotidianas. El comité de dirección reconoce que el
proceso de toma de decisiones sigue siendo muy centralizado y que la información
financiera no llega de forma oportuna a los equipos.
""",
            "filename": "mision_vision_valores.txt",
        },
        {
            "label": "Organigrama y Estructura Formal",
            "doc_type": "institutional",
            "content": """EMPRESA DEMO SAS — Estructura Organizacional (actualizado enero 2026)

DIRECCIÓN GENERAL (CEO)
└── Dirección de Operaciones
    ├── Equipo de Consultoría (3 personas)
    └── Administración y Finanzas (1 persona + apoyo externo)
└── Dirección de Tecnología
    └── Equipo de Desarrollo (5 personas)
└── Dirección de Capacitación
    └── Equipo de Capacitación (4 personas)

Total: 17 personas (incluyendo dirección)

NOTAS DE ESTRUCTURA:
- Todas las decisiones de presupuesto superiores a $500 USD requieren aprobación de Dirección General
- Los directores tienen autonomía para decisiones técnicas/operativas dentro de sus áreas
- La comunicación formal es vertical; se desalienta la comunicación lateral sin pasar por dirección
- Reunión de comité directivo: cada 2 semanas (asistencia obligatoria para los 3 directores)

CAMBIOS RECIENTES (post-reestructuración agosto 2025):
- Se creó el rol de Director de Operaciones (antes no existía)
- Se separó Capacitación de Operaciones
- Se eliminó el rol de Jefe de Proyectos (sus responsabilidades se distribuyeron)
""",
            "filename": "organigrama_estructura.txt",
        },
    ]

    docs_endpoint = f"/organizations/{org_id}/documents"
    for doc_info in docs_to_create:
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(doc_info["content"])
            tmp_path = f.name

        try:
            with open(tmp_path, "rb") as f:
                r = requests.post(
                    f"{BASE_URL}{docs_endpoint}",
                    headers={"Authorization": f"Bearer {token}"},
                    files={"file": (doc_info["filename"], f, "text/plain")},
                    data={
                        "label": doc_info["label"],
                        "doc_type": doc_info["doc_type"],
                    },
                    timeout=30,
                )
            if r.ok:
                log(f"  ✓ Documento: {doc_info['label']}")
            else:
                log(f"  ⚠ No se pudo subir documento '{doc_info['label']}': {r.status_code} — continuando")
        except Exception as e:
            log(f"  ⚠ Error subiendo documento: {e} — continuando")
        finally:
            os.unlink(tmp_path)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Seed de organización mock para testing del motor de análisis")
    parser.add_argument("--base-url", default="http://localhost:8000", help="URL base del backend")
    args = parser.parse_args()

    global BASE_URL
    BASE_URL = args.base_url.rstrip("/")

    print("=" * 60)
    print("  SEED — Empresa Demo SAS")
    print("=" * 60)

    log("Autenticando…")
    token, org_id = setup_auth()
    log(f"Token obtenido para org {org_id}")

    log("Actualizando org con contexto estratégico…")
    update_org(token, org_id)

    log("Creando nodos (8 en total)…")
    nodes = create_nodes(token, org_id)

    log("Creando miembros y entrevistas (6 de 8 nodos)…")
    create_members_and_interviews(token, org_id, nodes)

    log("Creando documentos institucionales mock…")
    create_mock_documents(token, org_id)

    print()
    print("=" * 60)
    print("  ✓ Seed completado")
    print()
    print("  Guarda estos valores en scripts/analysis/.env:")
    print()
    print(f"  DIAGNOSIS_API_TOKEN={token}")
    print(f"  # org_id = {org_id}")
    print()
    print("  Luego ejecuta:")
    print(f"  python run_analysis.py --org-id {org_id}")
    print("=" * 60)


if __name__ == "__main__":
    main()
