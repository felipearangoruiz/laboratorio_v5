"""Sprint 1.5 — Tests de la capa de compatibilidad (Sprint 1.4).

Automatiza el smoke-test manual de Sprint 1.4. Valida el espejado
transaccional Group↔Node(unit), Member↔Node(person), Interview↔NodeState
y las protecciones 409 introducidas por Sprint 1.4.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session, select

from app.core.security import create_access_token, hash_password
from app.models.campaign import AssessmentCampaign, CampaignStatus
from app.models.group import Group
from app.models.interview import Interview
from app.models.member import Member, MemberTokenStatus
from app.models.node import Node, NodeType
from app.models.node_state import NodeState, NodeStateStatus
from app.models.organization import Organization
from app.models.user import User, UserRole


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


def _create_member_with_mirror(
    session: Session,
    *,
    org_id,
    group_id,
    name: str,
    role_label: str,
    interview_token: str,
    parent_unit_id=None,
) -> Member:
    """Crea un Member + el Node(unit) espejo del group + el Node(person) espejo.

    Necesario porque el FK node_states.node_id → nodes exige un Node(person).
    En el flujo real, POST /groups y POST /members crean los espejos; aquí
    los construimos manualmente para probar el flujo del interview público
    sin depender de endpoints autenticados.
    """
    # Node(unit) espejo del group (si no existe)
    existing_unit = session.get(Node, group_id)
    if existing_unit is None:
        session.add(Node(
            id=group_id,
            organization_id=org_id,
            type=NodeType.UNIT,
            name="unit-mirror",
            position_x=0.0, position_y=0.0,
            attrs={},
        ))
        session.flush()

    member = Member(
        organization_id=org_id,
        group_id=group_id,
        name=name,
        role_label=role_label,
        interview_token=interview_token,
        token_status=MemberTokenStatus.PENDING,
    )
    session.add(member)
    session.flush()

    # Node(person) espejo del member
    session.add(Node(
        id=member.id,
        organization_id=org_id,
        parent_node_id=group_id,
        type=NodeType.PERSON,
        name=member.name,
        position_x=0.0, position_y=0.0,
        attrs={},
    ))
    session.commit()
    session.refresh(member)
    return member


@pytest.fixture
def seeded(session: Session) -> dict:
    """Org + admin + 1 group raíz."""
    org = Organization(name="OrgCompat", admin_id=None)
    session.add(org)
    session.flush()

    admin = User(
        email="compat-admin@test.com",
        hashed_password=hash_password("secret"),
        role=UserRole.ADMIN,
        organization_id=org.id,
    )
    session.add(admin)
    session.flush()

    root = Group(
        organization_id=org.id,
        name="Raíz",
        node_type="area",
        position_x=100.0,
        position_y=100.0,
    )
    session.add(root)
    session.commit()
    session.refresh(root)

    return {"org": org, "admin": admin, "root": root}


# ─────────────── Group ↔ Node(unit) ───────────────

def test_compat_create_group_espeja_node_unit(
    client: TestClient, session: Session, seeded: dict
) -> None:
    """POST /groups crea Node(unit) con el mismo UUID."""
    admin = seeded["admin"]
    r = client.post(
        "/groups",
        json={
            "organization_id": str(seeded["org"].id),
            "name": "NuevoGrupo",
            "description": "test",
            "position_x": 50.0,
            "position_y": 80.0,
        },
        headers=_auth(admin),
    )
    assert r.status_code == 201, r.text
    gid = r.json()["id"]

    node = session.get(Node, gid)
    assert node is not None
    assert node.type == NodeType.UNIT
    assert node.name == "NuevoGrupo"
    assert node.organization_id == seeded["org"].id


def test_compat_patch_group_actualiza_node(
    client: TestClient, session: Session, seeded: dict
) -> None:
    """PATCH /groups/{id} sincroniza nombre y posición en el Node espejo."""
    admin = seeded["admin"]
    root = seeded["root"]

    r = client.patch(
        f"/groups/{root.id}",
        json={"name": "RaízRenombrada", "position_x": 999.0},
        headers=_auth(admin),
    )
    assert r.status_code == 200, r.text

    session.expire_all()
    node = session.get(Node, root.id)
    assert node is not None
    assert node.name == "RaízRenombrada"
    assert node.position_x == 999.0


def test_compat_delete_group_sin_analisis_soft_delete_node(
    client: TestClient, session: Session, seeded: dict
) -> None:
    """DELETE /groups/{id} sin análisis → Group borrado + Node soft-deleted."""
    admin = seeded["admin"]
    # Crear un group fresco que no tenga análisis ni children ni members
    g = Group(organization_id=seeded["org"].id, name="ParaBorrar")
    session.add(g)
    session.commit()
    session.refresh(g)

    # El Node espejo sólo existe si se crea vía router. Aquí lo creamos
    # manualmente para verificar el soft-delete.
    session.add(Node(
        id=g.id,
        organization_id=g.id and seeded["org"].id,
        type=NodeType.UNIT,
        name=g.name,
        position_x=0.0, position_y=0.0,
        attrs={},
    ))
    session.commit()

    r = client.delete(f"/groups/{g.id}", headers=_auth(admin))
    assert r.status_code == 204, r.text

    assert session.get(Group, g.id) is None
    node = session.get(Node, g.id)
    assert node is not None
    assert node.deleted_at is not None  # soft-deleted


def test_compat_delete_group_con_analisis_devuelve_409(
    client: TestClient, session: Session, seeded: dict
) -> None:
    """DELETE /groups/{id} con NodeAnalysis asociado → 409."""
    admin = seeded["admin"]
    root = seeded["root"]

    # Crear AnalysisRun + NodeAnalysis que referencian root.id
    session.execute(
        text("""
            INSERT INTO analysis_runs (id, org_id, status, started_at)
            VALUES (:rid, :oid, 'completed', now())
        """),
        {"rid": str(uuid4()), "oid": str(seeded["org"].id)},
    )
    run_id = session.execute(
        text("SELECT id FROM analysis_runs WHERE org_id = :oid LIMIT 1"),
        {"oid": str(seeded["org"].id)},
    ).scalar_one()
    session.execute(
        text("""
            INSERT INTO node_analyses (id, run_id, org_id, group_id, created_at)
            VALUES (:nid, :rid, :oid, :gid, now())
        """),
        {
            "nid": str(uuid4()),
            "rid": str(run_id),
            "oid": str(seeded["org"].id),
            "gid": str(root.id),
        },
    )
    session.commit()

    r = client.delete(f"/groups/{root.id}", headers=_auth(admin))
    assert r.status_code == 409, r.text
    assert "análisis" in r.json()["detail"].lower()


# ─────────────── Member ↔ Node(person) ───────────────

def test_compat_create_member_espeja_node_person(
    client: TestClient, session: Session, seeded: dict
) -> None:
    """POST /members crea Node(person) con parent = Node(unit) del group."""
    admin = seeded["admin"]
    r = client.post(
        "/members",
        json={
            "organization_id": str(seeded["org"].id),
            "name": "Alice",
            "role_label": "Dev",
            "group_id": str(seeded["root"].id),
        },
        headers=_auth(admin),
    )
    assert r.status_code == 201, r.text
    mid = r.json()["id"]

    node = session.get(Node, mid)
    assert node is not None
    assert node.type == NodeType.PERSON
    assert node.name == "Alice"
    # parent_node_id debería ser el Node espejo del root group (si existe)
    # En este test el root fue creado directamente en DB — no hay mirror.
    # Validamos solo que el Node person se haya creado.


def test_compat_delete_member_con_analisis_devuelve_409(
    client: TestClient, session: Session, seeded: dict
) -> None:
    """DELETE /members/{id} con NodeAnalysis que referencia al member → 409."""
    admin = seeded["admin"]
    member = Member(
        organization_id=seeded["org"].id,
        group_id=seeded["root"].id,
        name="Bob",
        role_label="Analista",
    )
    session.add(member)
    session.commit()
    session.refresh(member)

    # El motor referencia via group_id (FK a groups). Aquí emulamos creando
    # un group fantasma con el mismo UUID del member y NodeAnalysis hacia él.
    # Más simple: creamos NodeAnalysis cuyo group_id = member.id, pero
    # `group_id` FK → groups, así que debemos insertar un group con ese UUID.
    # En producción, UUIDs preservados garantizan member.id también está en
    # `nodes` — pero NodeAnalysis.group_id apunta a `groups`. Por el FK,
    # necesitamos insertar en groups con member.id.
    session.execute(
        text("""
            INSERT INTO groups (id, organization_id, name, description, node_type,
                               position_x, position_y, created_at, tarea_general, email, area)
            VALUES (:gid, :oid, 'ghost-for-member', '', 'area', 0, 0, now(), '', '', '')
        """),
        {"gid": str(member.id), "oid": str(seeded["org"].id)},
    )
    session.execute(
        text("""
            INSERT INTO analysis_runs (id, org_id, status, started_at)
            VALUES (:rid, :oid, 'completed', now())
        """),
        {"rid": str(uuid4()), "oid": str(seeded["org"].id)},
    )
    run_id = session.execute(
        text("SELECT id FROM analysis_runs WHERE org_id = :oid ORDER BY started_at DESC LIMIT 1"),
        {"oid": str(seeded["org"].id)},
    ).scalar_one()
    session.execute(
        text("""
            INSERT INTO node_analyses (id, run_id, org_id, group_id, created_at)
            VALUES (:nid, :rid, :oid, :gid, now())
        """),
        {
            "nid": str(uuid4()),
            "rid": str(run_id),
            "oid": str(seeded["org"].id),
            "gid": str(member.id),
        },
    )
    session.commit()

    r = client.delete(f"/members/{member.id}", headers=_auth(admin))
    assert r.status_code == 409, r.text


# ─────────────── Interview ↔ NodeState ───────────────

def test_compat_submit_interview_crea_node_state_completed(
    client: TestClient, session: Session, seeded: dict
) -> None:
    """POST /entrevista/{token}/submit crea NodeState con status=COMPLETED."""
    member = _create_member_with_mirror(
        session,
        org_id=seeded["org"].id,
        group_id=seeded["root"].id,
        name="Carol",
        role_label="PM",
        interview_token="tok-test-submit-1",
    )

    r = client.post(
        f"/entrevista/{member.interview_token}/submit",
        json={"data": {"q1": 2}},
    )
    assert r.status_code == 200, r.text

    session.expire_all()
    ns = session.exec(select(NodeState).where(NodeState.node_id == member.id)).first()
    assert ns is not None
    assert ns.status == NodeStateStatus.COMPLETED
    assert ns.interview_data == {"q1": 2}
    assert ns.completed_at is not None


def test_compat_draft_interview_crea_node_state_in_progress(
    client: TestClient, session: Session, seeded: dict
) -> None:
    """POST /entrevista/{token}/draft crea NodeState con status=IN_PROGRESS."""
    member = _create_member_with_mirror(
        session,
        org_id=seeded["org"].id,
        group_id=seeded["root"].id,
        name="Dave",
        role_label="QA",
        interview_token="tok-test-draft-1",
    )

    r = client.post(
        f"/entrevista/{member.interview_token}/draft",
        json={"data": {"q1": 1}},
    )
    assert r.status_code == 200, r.text

    session.expire_all()
    ns = session.exec(select(NodeState).where(NodeState.node_id == member.id)).first()
    assert ns is not None
    assert ns.status == NodeStateStatus.IN_PROGRESS
    assert ns.completed_at is None


def test_compat_submit_interview_crea_diagnostico_inicial_on_the_fly(
    client: TestClient, session: Session, seeded: dict
) -> None:
    """Si no existe 'Diagnóstico Inicial' se crea con status=ACTIVE."""
    # La fixture `seeded` no crea campaign — validamos que submit la crea.
    member = _create_member_with_mirror(
        session,
        org_id=seeded["org"].id,
        group_id=seeded["root"].id,
        name="Eve",
        role_label="Dev",
        interview_token="tok-test-campaign-1",
    )

    # Precondición: no hay campaign
    pre = session.exec(
        select(AssessmentCampaign).where(
            AssessmentCampaign.organization_id == seeded["org"].id,
            AssessmentCampaign.name == "Diagnóstico Inicial",
        )
    ).all()
    assert len(pre) == 0

    r = client.post(
        f"/entrevista/{member.interview_token}/submit",
        json={"data": {"q1": 0}},
    )
    assert r.status_code == 200, r.text

    session.expire_all()
    post = session.exec(
        select(AssessmentCampaign).where(
            AssessmentCampaign.organization_id == seeded["org"].id,
            AssessmentCampaign.name == "Diagnóstico Inicial",
        )
    ).all()
    assert len(post) == 1
    assert post[0].status == CampaignStatus.ACTIVE
    assert post[0].created_by_user_id is None


def test_compat_interview_token_mapping_estado_member_a_node_state(
    client: TestClient, session: Session, seeded: dict
) -> None:
    """Tras submit: member.token_status=COMPLETED y NodeState.status=COMPLETED."""
    member = _create_member_with_mirror(
        session,
        org_id=seeded["org"].id,
        group_id=seeded["root"].id,
        name="Frank",
        role_label="Lead",
        interview_token="tok-test-mapping-1",
    )

    client.post(
        f"/entrevista/{member.interview_token}/submit",
        json={"data": {"q1": 2}},
    )

    session.expire_all()
    m = session.get(Member, member.id)
    ns = session.exec(select(NodeState).where(NodeState.node_id == member.id)).first()

    assert m.token_status == MemberTokenStatus.COMPLETED
    assert ns.status == NodeStateStatus.COMPLETED


def test_compat_submit_duplicado_devuelve_409(
    client: TestClient, session: Session, seeded: dict
) -> None:
    """Segundo submit sobre un interview ya COMPLETED → 409."""
    member = _create_member_with_mirror(
        session,
        org_id=seeded["org"].id,
        group_id=seeded["root"].id,
        name="Gina",
        role_label="Ops",
        interview_token="tok-test-dup-1",
    )

    r1 = client.post(
        f"/entrevista/{member.interview_token}/submit",
        json={"data": {"q1": 1}},
    )
    assert r1.status_code == 200

    r2 = client.post(
        f"/entrevista/{member.interview_token}/submit",
        json={"data": {"q1": 2}},
    )
    assert r2.status_code == 409, r2.text
