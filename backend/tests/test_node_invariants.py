"""Tests de las 13 invariantes de MODEL_PHILOSOPHY.md §8 (Sprint 1.5).

Convención de nombres (D10):
  - ``test_router_*``  → ejercita el nivel 1 (HTTP → 422/409) vía TestClient.
  - ``test_db_*``      → ejercita el nivel 2 (escritura directa vía ORM).

Política (§8.1): las invariantes todavía sin constraint de base de datos se
marcan con ``@pytest.mark.xfail`` en los tests ``test_db_*``. Esto deja la
deuda visible en la suite en lugar de ocultarla.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.security import create_access_token, hash_password
from app.models.campaign import AssessmentCampaign, CampaignStatus
from app.models.edge import Edge, EdgeType
from app.models.node import Node, NodeType
from app.models.node_state import NodeState, NodeStateStatus
from app.models.organization import Organization
from app.models.user import User, UserRole


# ─────────────────────────── Fixture: seed ────────────────────────────

@pytest.fixture
def seeded(session: Session) -> dict:
    own_org = Organization(name="Inv Org", description="", sector="tech")
    other_org = Organization(name="Inv Other", description="", sector="retail")
    session.add(own_org)
    session.add(other_org)
    session.commit()
    session.refresh(own_org)
    session.refresh(other_org)

    admin = User(
        email="inv-admin@test.com",
        hashed_password=hash_password("secret"),
        role=UserRole.ADMIN,
        organization_id=own_org.id,
    )
    superadmin = User(
        email="inv-super@test.com",
        hashed_password=hash_password("secret"),
        role=UserRole.SUPERADMIN,
        organization_id=own_org.id,
    )
    session.add(admin)
    session.add(superadmin)
    session.commit()

    root_unit = Node(
        organization_id=own_org.id,
        parent_node_id=None,
        type=NodeType.UNIT,
        name="Root Unit",
    )
    other_unit = Node(
        organization_id=other_org.id,
        parent_node_id=None,
        type=NodeType.UNIT,
        name="Other Unit",
    )
    session.add(root_unit)
    session.add(other_unit)
    session.commit()
    session.refresh(root_unit)
    session.refresh(other_unit)

    return {
        "own_org": own_org,
        "other_org": other_org,
        "admin": admin,
        "superadmin": superadmin,
        "root_unit": root_unit,
        "other_unit": other_unit,
    }


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


# ══════════════════════════════════════════════════════════════════════
# INVARIANTE 1 — Scope organizacional
# ══════════════════════════════════════════════════════════════════════

def test_router_node_requiere_organization_id(client: TestClient, seeded: dict) -> None:
    # organization_id ausente → 422 por Pydantic
    r = client.post(
        "/nodes",
        json={"type": "unit", "name": "missing org"},
        headers=_auth(seeded["superadmin"]),
    )
    assert r.status_code == 422


def test_router_node_con_organization_id_valido(client: TestClient, seeded: dict) -> None:
    r = client.post(
        "/nodes",
        json={
            "organization_id": str(seeded["own_org"].id),
            "type": "unit",
            "name": "New Unit",
        },
        headers=_auth(seeded["admin"]),
    )
    assert r.status_code == 201, r.text


def test_router_parent_debe_ser_misma_organizacion(client: TestClient, seeded: dict) -> None:
    # superadmin para evitar 403; violación = 422 por scope organizacional
    r = client.post(
        "/nodes",
        json={
            "organization_id": str(seeded["own_org"].id),
            "type": "unit",
            "name": "cross-org child",
            "parent_node_id": str(seeded["other_unit"].id),
        },
        headers=_auth(seeded["superadmin"]),
    )
    assert r.status_code == 422


# ══════════════════════════════════════════════════════════════════════
# INVARIANTE 2 — Tipo discreto (unit | person)
# ══════════════════════════════════════════════════════════════════════

def test_router_node_type_invalido_rechazado(client: TestClient, seeded: dict) -> None:
    r = client.post(
        "/nodes",
        json={
            "organization_id": str(seeded["own_org"].id),
            "type": "robot",
            "name": "invalid type",
        },
        headers=_auth(seeded["admin"]),
    )
    assert r.status_code == 422


def test_router_node_type_person_valido(client: TestClient, seeded: dict) -> None:
    r = client.post(
        "/nodes",
        json={
            "organization_id": str(seeded["own_org"].id),
            "type": "person",
            "name": "Alice",
            "parent_node_id": str(seeded["root_unit"].id),
        },
        headers=_auth(seeded["admin"]),
    )
    assert r.status_code == 201, r.text


# ══════════════════════════════════════════════════════════════════════
# INVARIANTE 3 — person requiere parent unit
# ══════════════════════════════════════════════════════════════════════

def test_router_person_sin_parent_rechazado(client: TestClient, seeded: dict) -> None:
    r = client.post(
        "/nodes",
        json={
            "organization_id": str(seeded["own_org"].id),
            "type": "person",
            "name": "orphan person",
        },
        headers=_auth(seeded["admin"]),
    )
    assert r.status_code == 422


def test_router_person_parent_de_person_rechazado(client: TestClient, seeded: dict) -> None:
    # Crea una person válida primero
    r = client.post(
        "/nodes",
        json={
            "organization_id": str(seeded["own_org"].id),
            "type": "person",
            "name": "parent-person",
            "parent_node_id": str(seeded["root_unit"].id),
        },
        headers=_auth(seeded["admin"]),
    )
    assert r.status_code == 201
    parent_person_id = r.json()["id"]

    # Intentar colgar otra person de la anterior → parent.type != unit
    r2 = client.post(
        "/nodes",
        json={
            "organization_id": str(seeded["own_org"].id),
            "type": "person",
            "name": "child-person",
            "parent_node_id": parent_person_id,
        },
        headers=_auth(seeded["admin"]),
    )
    assert r2.status_code == 422


# ══════════════════════════════════════════════════════════════════════
# INVARIANTE 4 — unit puede ser raíz; unit parent debe ser unit
# ══════════════════════════════════════════════════════════════════════

def test_router_unit_raiz_permitido(client: TestClient, seeded: dict) -> None:
    r = client.post(
        "/nodes",
        json={
            "organization_id": str(seeded["own_org"].id),
            "type": "unit",
            "name": "another root",
        },
        headers=_auth(seeded["admin"]),
    )
    assert r.status_code == 201


def test_router_unit_parent_de_unit_rechazado_si_parent_es_person(
    client: TestClient, seeded: dict
) -> None:
    # Crear una person
    r = client.post(
        "/nodes",
        json={
            "organization_id": str(seeded["own_org"].id),
            "type": "person",
            "name": "some-person",
            "parent_node_id": str(seeded["root_unit"].id),
        },
        headers=_auth(seeded["admin"]),
    )
    assert r.status_code == 201
    person_id = r.json()["id"]

    # Intentar que un unit cuelgue de una person
    r2 = client.post(
        "/nodes",
        json={
            "organization_id": str(seeded["own_org"].id),
            "type": "unit",
            "name": "bad-child-unit",
            "parent_node_id": person_id,
        },
        headers=_auth(seeded["admin"]),
    )
    assert r2.status_code == 422


# ══════════════════════════════════════════════════════════════════════
# INVARIANTE 5 — Árbol acíclico en parent_node_id
# ══════════════════════════════════════════════════════════════════════

def test_router_ciclo_detectado_en_patch(client: TestClient, seeded: dict) -> None:
    # Crear A → B (B hijo de A), luego intentar que A sea hijo de B
    r1 = client.post(
        "/nodes",
        json={
            "organization_id": str(seeded["own_org"].id),
            "type": "unit",
            "name": "A",
        },
        headers=_auth(seeded["admin"]),
    )
    a_id = r1.json()["id"]
    r2 = client.post(
        "/nodes",
        json={
            "organization_id": str(seeded["own_org"].id),
            "type": "unit",
            "name": "B",
            "parent_node_id": a_id,
        },
        headers=_auth(seeded["admin"]),
    )
    b_id = r2.json()["id"]

    r3 = client.patch(
        f"/nodes/{a_id}",
        json={"parent_node_id": b_id},
        headers=_auth(seeded["admin"]),
    )
    assert r3.status_code == 422


def test_router_self_parent_rechazado(client: TestClient, seeded: dict) -> None:
    r = client.post(
        "/nodes",
        json={
            "organization_id": str(seeded["own_org"].id),
            "type": "unit",
            "name": "self-parent",
        },
        headers=_auth(seeded["admin"]),
    )
    node_id = r.json()["id"]
    r2 = client.patch(
        f"/nodes/{node_id}",
        json={"parent_node_id": node_id},
        headers=_auth(seeded["admin"]),
    )
    assert r2.status_code == 422


# ══════════════════════════════════════════════════════════════════════
# INVARIANTE 6 — Edges inter-unit exclusivos
# ══════════════════════════════════════════════════════════════════════

def test_router_edge_con_person_rechazado(client: TestClient, seeded: dict) -> None:
    # Crear una person
    r = client.post(
        "/nodes",
        json={
            "organization_id": str(seeded["own_org"].id),
            "type": "person",
            "name": "edge-person",
            "parent_node_id": str(seeded["root_unit"].id),
        },
        headers=_auth(seeded["admin"]),
    )
    person_id = r.json()["id"]

    r2 = client.post(
        "/edges",
        json={
            "organization_id": str(seeded["own_org"].id),
            "source_node_id": str(seeded["root_unit"].id),
            "target_node_id": person_id,
            "edge_type": "lateral",
        },
        headers=_auth(seeded["admin"]),
    )
    assert r2.status_code == 422


def test_router_edge_entre_units_permitido(client: TestClient, seeded: dict) -> None:
    # Crear segundo unit
    r = client.post(
        "/nodes",
        json={
            "organization_id": str(seeded["own_org"].id),
            "type": "unit",
            "name": "Second Unit",
        },
        headers=_auth(seeded["admin"]),
    )
    second_id = r.json()["id"]

    r2 = client.post(
        "/edges",
        json={
            "organization_id": str(seeded["own_org"].id),
            "source_node_id": str(seeded["root_unit"].id),
            "target_node_id": second_id,
            "edge_type": "lateral",
        },
        headers=_auth(seeded["admin"]),
    )
    assert r2.status_code == 201, r2.text


# ══════════════════════════════════════════════════════════════════════
# INVARIANTE 7 — No self-loop, unicidad dirigida
# ══════════════════════════════════════════════════════════════════════

def test_router_edge_self_loop_rechazado(client: TestClient, seeded: dict) -> None:
    r = client.post(
        "/edges",
        json={
            "organization_id": str(seeded["own_org"].id),
            "source_node_id": str(seeded["root_unit"].id),
            "target_node_id": str(seeded["root_unit"].id),
            "edge_type": "lateral",
        },
        headers=_auth(seeded["admin"]),
    )
    assert r.status_code == 422


def test_router_edge_duplicado_rechazado(client: TestClient, seeded: dict) -> None:
    # Crear segundo unit y un edge
    r = client.post(
        "/nodes",
        json={
            "organization_id": str(seeded["own_org"].id),
            "type": "unit",
            "name": "U2",
        },
        headers=_auth(seeded["admin"]),
    )
    u2 = r.json()["id"]
    r1 = client.post(
        "/edges",
        json={
            "organization_id": str(seeded["own_org"].id),
            "source_node_id": str(seeded["root_unit"].id),
            "target_node_id": u2,
            "edge_type": "lateral",
        },
        headers=_auth(seeded["admin"]),
    )
    assert r1.status_code == 201
    # Mismo edge duplicado
    r2 = client.post(
        "/edges",
        json={
            "organization_id": str(seeded["own_org"].id),
            "source_node_id": str(seeded["root_unit"].id),
            "target_node_id": u2,
            "edge_type": "lateral",
        },
        headers=_auth(seeded["admin"]),
    )
    assert r2.status_code == 409


# ══════════════════════════════════════════════════════════════════════
# INVARIANTE 8 — Enum cerrado de edge_type
# ══════════════════════════════════════════════════════════════════════

def test_router_edge_type_hierarchical_rechazado(client: TestClient, seeded: dict) -> None:
    r = client.post(
        "/nodes",
        json={
            "organization_id": str(seeded["own_org"].id),
            "type": "unit",
            "name": "E1",
        },
        headers=_auth(seeded["admin"]),
    )
    e1 = r.json()["id"]
    r2 = client.post(
        "/edges",
        json={
            "organization_id": str(seeded["own_org"].id),
            "source_node_id": str(seeded["root_unit"].id),
            "target_node_id": e1,
            "edge_type": "hierarchical",
        },
        headers=_auth(seeded["admin"]),
    )
    assert r2.status_code == 422


def test_router_edge_type_lateral_valido(client: TestClient, seeded: dict) -> None:
    r = client.post(
        "/nodes",
        json={
            "organization_id": str(seeded["own_org"].id),
            "type": "unit",
            "name": "E2",
        },
        headers=_auth(seeded["admin"]),
    )
    e2 = r.json()["id"]
    r2 = client.post(
        "/edges",
        json={
            "organization_id": str(seeded["own_org"].id),
            "source_node_id": str(seeded["root_unit"].id),
            "target_node_id": e2,
            "edge_type": "lateral",
        },
        headers=_auth(seeded["admin"]),
    )
    assert r2.status_code == 201


# ══════════════════════════════════════════════════════════════════════
# INVARIANTE 9 — Identidad inmutable (type no se cambia)
# ══════════════════════════════════════════════════════════════════════

def test_router_patch_no_permite_cambiar_type(client: TestClient, seeded: dict) -> None:
    # Crear unit
    r = client.post(
        "/nodes",
        json={
            "organization_id": str(seeded["own_org"].id),
            "type": "unit",
            "name": "Immutable",
        },
        headers=_auth(seeded["admin"]),
    )
    node_id = r.json()["id"]
    # PATCH intenta cambiar type — el schema NodeUpdate no lo admite y se ignora
    r2 = client.patch(
        f"/nodes/{node_id}",
        json={"type": "person"},
        headers=_auth(seeded["admin"]),
    )
    assert r2.status_code == 200
    # El type se mantuvo unit (campo filtrado por el schema)
    assert r2.json()["type"] == "unit"


def test_router_patch_name_permitido(client: TestClient, seeded: dict) -> None:
    r = client.patch(
        f"/nodes/{seeded['root_unit'].id}",
        json={"name": "Renamed Unit"},
        headers=_auth(seeded["admin"]),
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed Unit"


# ══════════════════════════════════════════════════════════════════════
# INVARIANTE 10 — NodeState UNIQUE (node_id, campaign_id)
# ══════════════════════════════════════════════════════════════════════

def _make_campaign(
    session: Session, org_id, status_value: CampaignStatus = CampaignStatus.ACTIVE
) -> AssessmentCampaign:
    c = AssessmentCampaign(
        organization_id=org_id,
        name=f"Camp {uuid4().hex[:8]}",
        status=status_value,
        started_at=datetime.now(timezone.utc),
    )
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


def test_router_node_state_duplicado_rechazado(
    client: TestClient, session: Session, seeded: dict
) -> None:
    camp = _make_campaign(session, seeded["own_org"].id)
    payload = {
        "node_id": str(seeded["root_unit"].id),
        "campaign_id": str(camp.id),
        "status": "invited",
    }
    r1 = client.post("/node-states", json=payload, headers=_auth(seeded["admin"]))
    assert r1.status_code == 201
    r2 = client.post("/node-states", json=payload, headers=_auth(seeded["admin"]))
    assert r2.status_code == 409


def test_db_node_state_unique_constraint(
    session: Session, seeded: dict
) -> None:
    """Escritura directa vía ORM — la DB enforza UNIQUE (node_id, campaign_id)."""
    camp = _make_campaign(session, seeded["own_org"].id)
    ns1 = NodeState(
        node_id=seeded["root_unit"].id,
        campaign_id=camp.id,
        status=NodeStateStatus.INVITED,
    )
    session.add(ns1)
    session.commit()

    ns2 = NodeState(
        node_id=seeded["root_unit"].id,
        campaign_id=camp.id,
        status=NodeStateStatus.INVITED,
    )
    session.add(ns2)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


# ══════════════════════════════════════════════════════════════════════
# INVARIANTE 11 — A lo sumo una campaña active por org
# ══════════════════════════════════════════════════════════════════════

def test_router_segunda_campaign_active_rechazada(
    client: TestClient, session: Session, seeded: dict
) -> None:
    # Ya existe una activa
    _make_campaign(session, seeded["own_org"].id, CampaignStatus.ACTIVE)
    r = client.post(
        "/campaigns",
        json={
            "organization_id": str(seeded["own_org"].id),
            "name": "Second Active",
            "status": "active",
        },
        headers=_auth(seeded["admin"]),
    )
    assert r.status_code == 422


def test_router_campaign_active_y_draft_coexisten(
    client: TestClient, session: Session, seeded: dict
) -> None:
    _make_campaign(session, seeded["own_org"].id, CampaignStatus.ACTIVE)
    r = client.post(
        "/campaigns",
        json={
            "organization_id": str(seeded["own_org"].id),
            "name": "Draft Coexist",
            "status": "draft",
        },
        headers=_auth(seeded["admin"]),
    )
    assert r.status_code == 201


@pytest.mark.xfail(reason="invariante solo enforzada a nivel router hasta Sprint 1.6")
def test_db_segunda_campaign_active_rechazada(session: Session, seeded: dict) -> None:
    c1 = AssessmentCampaign(
        organization_id=seeded["own_org"].id,
        name="DB Active 1",
        status=CampaignStatus.ACTIVE,
    )
    c2 = AssessmentCampaign(
        organization_id=seeded["own_org"].id,
        name="DB Active 2",
        status=CampaignStatus.ACTIVE,
    )
    session.add(c1)
    session.add(c2)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


# ══════════════════════════════════════════════════════════════════════
# INVARIANTE 12 — Documents consistentes (org == campaign.org)
# ══════════════════════════════════════════════════════════════════════

def test_router_node_state_org_mismatch_rechazado(
    client: TestClient, session: Session, seeded: dict
) -> None:
    """Scope organizacional también aplica a NodeState (variante de inv. 12
    que es la forma en que este motor expresa el cruce de orgs)."""
    camp_other = _make_campaign(session, seeded["other_org"].id)
    r = client.post(
        "/node-states",
        json={
            "node_id": str(seeded["root_unit"].id),
            "campaign_id": str(camp_other.id),
            "status": "invited",
        },
        headers=_auth(seeded["superadmin"]),
    )
    assert r.status_code == 422


def test_router_node_state_misma_org_permitido(
    client: TestClient, session: Session, seeded: dict
) -> None:
    camp = _make_campaign(session, seeded["own_org"].id)
    r = client.post(
        "/node-states",
        json={
            "node_id": str(seeded["root_unit"].id),
            "campaign_id": str(camp.id),
            "status": "invited",
        },
        headers=_auth(seeded["admin"]),
    )
    assert r.status_code == 201


# ══════════════════════════════════════════════════════════════════════
# INVARIANTE 13 — Edge type=process requiere order entero positivo
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture
def two_units(client: TestClient, seeded: dict) -> tuple[str, str]:
    r = client.post(
        "/nodes",
        json={
            "organization_id": str(seeded["own_org"].id),
            "type": "unit",
            "name": "P1",
        },
        headers=_auth(seeded["admin"]),
    )
    u1 = r.json()["id"]
    r = client.post(
        "/nodes",
        json={
            "organization_id": str(seeded["own_org"].id),
            "type": "unit",
            "name": "P2",
        },
        headers=_auth(seeded["admin"]),
    )
    u2 = r.json()["id"]
    return u1, u2


def test_router_edge_process_sin_order_rechazado(
    client: TestClient, seeded: dict, two_units: tuple[str, str]
) -> None:
    u1, u2 = two_units
    r = client.post(
        "/edges",
        json={
            "organization_id": str(seeded["own_org"].id),
            "source_node_id": u1,
            "target_node_id": u2,
            "edge_type": "process",
            "edge_metadata": {},
        },
        headers=_auth(seeded["admin"]),
    )
    assert r.status_code == 422


def test_router_edge_process_order_negativo_rechazado(
    client: TestClient, seeded: dict, two_units: tuple[str, str]
) -> None:
    u1, u2 = two_units
    r = client.post(
        "/edges",
        json={
            "organization_id": str(seeded["own_org"].id),
            "source_node_id": u1,
            "target_node_id": u2,
            "edge_type": "process",
            "edge_metadata": {"order": -1},
        },
        headers=_auth(seeded["admin"]),
    )
    assert r.status_code == 422


def test_router_edge_process_order_positivo_valido(
    client: TestClient, seeded: dict, two_units: tuple[str, str]
) -> None:
    u1, u2 = two_units
    r = client.post(
        "/edges",
        json={
            "organization_id": str(seeded["own_org"].id),
            "source_node_id": u1,
            "target_node_id": u2,
            "edge_type": "process",
            "edge_metadata": {"order": 3},
        },
        headers=_auth(seeded["admin"]),
    )
    assert r.status_code == 201


def test_router_edge_lateral_sin_order_permitido(
    client: TestClient, seeded: dict, two_units: tuple[str, str]
) -> None:
    u1, u2 = two_units
    r = client.post(
        "/edges",
        json={
            "organization_id": str(seeded["own_org"].id),
            "source_node_id": u1,
            "target_node_id": u2,
            "edge_type": "lateral",
            "edge_metadata": {},
        },
        headers=_auth(seeded["admin"]),
    )
    assert r.status_code == 201
