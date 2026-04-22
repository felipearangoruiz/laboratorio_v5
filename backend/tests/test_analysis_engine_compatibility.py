"""Sprint 1.5 — Compatibilidad del motor de análisis post-migración.

Prueba CRÍTICA: el motor de análisis (pipeline externo + endpoints
/analysis/...) debe seguir funcionando después de la migración Sprint 1.2.

Por qué es crítica
──────────────────
`NodeAnalysis.group_id` es un FK a `groups.id`. La migración preserva los
UUIDs (Group.id → Node.id), por lo que ese mismo UUID también existe en
la nueva tabla `nodes`. Este test ejecuta el pipeline COMPLETO sobre datos
recién migrados y valida que:

- POST /runs → POST /nodes/{group_id} → POST /groups/{group_id}
  → POST /org → POST /findings todos responden 2xx.
- `NodeAnalysis.group_id` apunta a un UUID que existe tanto en `groups`
  como en `nodes` (invariante de UUID preservado).
- GET /analysis/latest/nodes/{group_id} devuelve lo grabado.

Mock del LLM
────────────
El motor vive en un script externo; el backend sólo almacena. Los "LLM
responses" son JSON que simulamos enviando al endpoint de escritura.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session, select

from app.core.security import create_access_token, hash_password
from app.models.group import Group
from app.models.interview import Interview
from app.models.member import Member, MemberTokenStatus
from app.models.node import Node
from app.models.organization import Organization
from app.models.user import User, UserRole
from scripts.migrate_data_to_new_model import (
    DualLog,
    migrate_campaigns,
    migrate_groups_to_nodes,
    migrate_interviews_to_node_states,
    migrate_members_to_nodes,
)

_FIXTURES = Path(__file__).parent / "fixtures" / "llm_responses"


def _load(name: str) -> dict:
    with open(_FIXTURES / name, encoding="utf-8") as fh:
        return json.load(fh)


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


# ─────────────────── Fixture: datos legacy + migrados ───────────────────

@pytest.fixture
def migrated_scenario(session: Session) -> dict:
    """Crea 1 org + 1 group + 3 members con interviews submitted, y migra."""
    now = datetime.now(timezone.utc)

    org = Organization(name="OrgMotor", admin_id=None, created_at=now - timedelta(days=30))
    session.add(org)
    session.flush()

    user = User(
        email="admin@motor.test",
        hashed_password=hash_password("secret"),
        role=UserRole.ADMIN,
        organization_id=org.id,
    )
    session.add(user)
    session.flush()

    group = Group(
        organization_id=org.id,
        name="Equipo Operaciones",
        node_type="area",
        position_x=100.0,
        position_y=100.0,
        created_at=now - timedelta(days=25),
    )
    session.add(group)
    session.flush()

    members: list[Member] = []
    for i in range(3):
        m = Member(
            organization_id=org.id,
            group_id=group.id,
            name=f"Miembro-{i}",
            role_label="Analista",
            token_status=MemberTokenStatus.COMPLETED,
            created_at=now - timedelta(days=10),
        )
        members.append(m)
    session.add_all(members)
    session.flush()

    interviews: list[Interview] = []
    for m in members:
        iv = Interview(
            member_id=m.id,
            organization_id=org.id,
            group_id=group.id,
            data={"q1": 3, "q2": "Respuesta libre con contenido sustantivo y detalle"},
            submitted_at=now - timedelta(days=1),
        )
        interviews.append(iv)
    session.add_all(interviews)
    session.flush()

    # ── Ejecutar migración ───────────────────────────────────────────
    log = DualLog()
    orgs = list(session.exec(select(Organization)).all())
    groups = list(session.exec(select(Group)).all())
    mems = list(session.exec(select(Member)).all())
    ivs = list(session.exec(select(Interview)).all())

    org_to_campaign = migrate_campaigns(session, orgs, log)
    root_units = migrate_groups_to_nodes(session, groups, log)
    migrate_members_to_nodes(
        session, mems, root_units, {o.id for o in orgs}, {g.id for g in groups}, log,
    )
    migrate_interviews_to_node_states(
        session, ivs, org_to_campaign,
        {m.id: m.organization_id for m in mems},
        {m.id: m.interview_token for m in mems},
        {m.id: m.role_label for m in mems},
        {m.id: m.created_at for m in mems},
        log,
    )
    session.flush()

    return {
        "org": org,
        "user": user,
        "group": group,
        "members": members,
        "interviews": interviews,
        "campaign_id": org_to_campaign[org.id],
    }


# ─────────────────── Tests ───────────────────

def test_pipeline_completo_post_migracion(
    client: TestClient, session: Session, migrated_scenario: dict
) -> None:
    """Ejecuta el pipeline completo (run → node → group → org → findings)."""
    org = migrated_scenario["org"]
    user = migrated_scenario["user"]
    group = migrated_scenario["group"]
    headers = _auth(user)

    # 1. Abrir corrida
    r = client.post(
        f"/organizations/{org.id}/analysis/runs",
        json={"model_used": "test-mock", "total_nodes": 1, "total_groups": 1},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    run_id = r.json()["run_id"]
    assert r.json()["status"] == "running"

    # 2. Paso 1 — NodeAnalysis
    payload = _load("node_analysis.json")
    payload.update({"run_id": run_id, "org_id": str(org.id), "group_id": str(group.id)})
    r = client.post(
        f"/analysis/runs/{run_id}/nodes/{group.id}",
        json=payload,
        headers=headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["group_id"] == str(group.id)

    # 3. Paso 2 — GroupAnalysis
    payload = _load("group_analysis.json")
    payload.update({"run_id": run_id, "org_id": str(org.id), "group_id": str(group.id)})
    r = client.post(
        f"/analysis/runs/{run_id}/groups/{group.id}",
        json=payload,
        headers=headers,
    )
    assert r.status_code == 201, r.text

    # 4. Paso 3 — OrgAnalysis
    payload = _load("org_analysis.json")
    payload.update({"run_id": run_id, "org_id": str(org.id)})
    r = client.post(
        f"/analysis/runs/{run_id}/org",
        json=payload,
        headers=headers,
    )
    assert r.status_code == 201, r.text

    # 5. Paso 4 — Findings + cierre
    payload = _load("findings.json")
    r = client.post(
        f"/analysis/runs/{run_id}/findings",
        json=payload,
        headers=headers,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["findings_created"] == 1
    assert body["recommendations_created"] == 1


def test_node_analysis_group_id_existe_en_groups_y_nodes(
    client: TestClient, session: Session, migrated_scenario: dict
) -> None:
    """INVARIANTE UUID: NodeAnalysis.group_id debe existir en `groups` y `nodes`."""
    org = migrated_scenario["org"]
    user = migrated_scenario["user"]
    group = migrated_scenario["group"]
    headers = _auth(user)

    # Crear corrida + node_analysis
    r = client.post(
        f"/organizations/{org.id}/analysis/runs",
        json={"model_used": "test", "total_nodes": 1, "total_groups": 1},
        headers=headers,
    )
    run_id = r.json()["run_id"]

    payload = _load("node_analysis.json")
    payload.update({"run_id": run_id, "org_id": str(org.id), "group_id": str(group.id)})
    r = client.post(
        f"/analysis/runs/{run_id}/nodes/{group.id}",
        json=payload,
        headers=headers,
    )
    assert r.status_code == 201, r.text
    saved_group_id = r.json()["group_id"]

    # Comprobar que el mismo UUID existe en AMBAS tablas
    in_groups = session.exec(
        text(f"SELECT 1 FROM groups WHERE id = '{saved_group_id}'")
    ).first()
    in_nodes = session.exec(
        text(f"SELECT 1 FROM nodes WHERE id = '{saved_group_id}'")
    ).first()
    assert in_groups is not None, "group_id no existe en groups tras crear NodeAnalysis"
    assert in_nodes is not None, "UUID no preservado: ausente en la tabla nodes"

    # Y verificamos vía ORM que el Node correspondiente es un unit
    node = session.get(Node, group.id)
    assert node is not None
    assert node.organization_id == org.id


def test_get_latest_node_analysis_funciona_post_migracion(
    client: TestClient, session: Session, migrated_scenario: dict
) -> None:
    """El endpoint de lectura `latest/nodes/{group_id}` consulta group_id sin romperse."""
    org = migrated_scenario["org"]
    user = migrated_scenario["user"]
    group = migrated_scenario["group"]
    headers = _auth(user)

    # Pipeline completo mínimo para cerrar la corrida
    r = client.post(
        f"/organizations/{org.id}/analysis/runs",
        json={"model_used": "t", "total_nodes": 1, "total_groups": 1},
        headers=headers,
    )
    run_id = r.json()["run_id"]

    payload_node = _load("node_analysis.json")
    payload_node.update({"run_id": run_id, "org_id": str(org.id), "group_id": str(group.id)})
    client.post(
        f"/analysis/runs/{run_id}/nodes/{group.id}",
        json=payload_node, headers=headers,
    )

    # Cierra la corrida con findings vacíos para que status=completed
    r = client.post(
        f"/analysis/runs/{run_id}/findings",
        json={"findings": [], "recommendations": [], "narrative_md": "", "executive_summary": ""},
        headers=headers,
    )
    assert r.status_code == 201, r.text

    # Lectura
    r = client.get(
        f"/organizations/{org.id}/analysis/latest/nodes/{group.id}",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data is not None
    assert data["group_id"] == str(group.id)
    assert data["themes"] == payload_node["themes"]


def test_analysis_input_bundle_usa_tablas_legacy(
    client: TestClient, session: Session, migrated_scenario: dict
) -> None:
    """GET /analysis/input sigue consultando groups/members/interviews (compat)."""
    org = migrated_scenario["org"]
    user = migrated_scenario["user"]
    headers = _auth(user)

    r = client.get(f"/organizations/{org.id}/analysis/input", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["organization"]["id"] == str(org.id)
    assert data["structure"]["total_nodes"] == 1
    assert data["structure"]["total_with_interview"] == 1
    assert data["interviews"]["total_completed"] == 3
