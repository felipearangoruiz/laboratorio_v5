"""Tests para PATCH /organizations/{org_id}/nodes/positions.

Creado en el Sprint de auto-layout: reemplaza al endpoint legacy
`/organizations/{org_id}/groups/positions`, que sólo actualizaba
Groups y dejaba las posiciones de persons sin persistencia.
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, hash_password
from app.models.node import Node, NodeType
from app.models.organization import Organization
from app.models.user import User, UserRole


@pytest.fixture
def seed(session: Session) -> dict:
    own_org = Organization(name="Pos Org", description="", sector="tech")
    other_org = Organization(name="Other Org", description="", sector="retail")
    session.add(own_org)
    session.add(other_org)
    session.commit()
    session.refresh(own_org)
    session.refresh(other_org)

    admin = User(
        email="pos-admin@test.com",
        hashed_password=hash_password("secret"),
        role=UserRole.ADMIN,
        organization_id=own_org.id,
    )
    other_admin = User(
        email="pos-other-admin@test.com",
        hashed_password=hash_password("secret"),
        role=UserRole.ADMIN,
        organization_id=other_org.id,
    )
    session.add(admin)
    session.add(other_admin)
    session.commit()

    unit = Node(
        organization_id=own_org.id,
        parent_node_id=None,
        type=NodeType.UNIT,
        name="Root Unit",
        position_x=0.0,
        position_y=0.0,
    )
    session.add(unit)
    session.commit()
    session.refresh(unit)

    person = Node(
        organization_id=own_org.id,
        parent_node_id=unit.id,
        type=NodeType.PERSON,
        name="Alice",
        position_x=0.0,
        position_y=0.0,
    )
    other_unit = Node(
        organization_id=other_org.id,
        parent_node_id=None,
        type=NodeType.UNIT,
        name="Other Unit",
        position_x=10.0,
        position_y=20.0,
    )
    session.add(person)
    session.add(other_unit)
    session.commit()
    session.refresh(person)
    session.refresh(other_unit)

    return {
        "own_org": own_org,
        "other_org": other_org,
        "admin": admin,
        "other_admin": other_admin,
        "unit": unit,
        "person": person,
        "other_unit": other_unit,
    }


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


def test_bulk_positions_updates_unit_and_person(
    client: TestClient, session: Session, seed: dict
) -> None:
    r = client.patch(
        f"/organizations/{seed['own_org'].id}/nodes/positions",
        json={
            "positions": [
                {"id": str(seed["unit"].id), "x": 100.0, "y": 200.0},
                {"id": str(seed["person"].id), "x": 300.5, "y": 400.75},
            ]
        },
        headers=_auth(seed["admin"]),
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"updated": 2}

    session.expire_all()
    unit_after = session.get(Node, seed["unit"].id)
    person_after = session.get(Node, seed["person"].id)
    assert unit_after is not None and person_after is not None
    assert unit_after.position_x == 100.0 and unit_after.position_y == 200.0
    assert person_after.position_x == 300.5 and person_after.position_y == 400.75


def test_bulk_positions_rejects_cross_org(
    client: TestClient, session: Session, seed: dict
) -> None:
    # Admin de own_org intenta mover un nodo de other_org → se ignora silenciosamente.
    r = client.patch(
        f"/organizations/{seed['own_org'].id}/nodes/positions",
        json={
            "positions": [
                {"id": str(seed["other_unit"].id), "x": 999.0, "y": 999.0},
            ]
        },
        headers=_auth(seed["admin"]),
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"updated": 0}

    session.expire_all()
    other_after = session.get(Node, seed["other_unit"].id)
    assert other_after is not None
    assert other_after.position_x == 10.0 and other_after.position_y == 20.0


def test_bulk_positions_403_when_not_member_of_org(
    client: TestClient, seed: dict
) -> None:
    # Admin de other_org no puede invocar el endpoint sobre own_org.
    r = client.patch(
        f"/organizations/{seed['own_org'].id}/nodes/positions",
        json={"positions": [{"id": str(seed["unit"].id), "x": 1.0, "y": 2.0}]},
        headers=_auth(seed["other_admin"]),
    )
    assert r.status_code == 403


def test_bulk_positions_ignores_unknown_ids(
    client: TestClient, seed: dict
) -> None:
    r = client.patch(
        f"/organizations/{seed['own_org'].id}/nodes/positions",
        json={
            "positions": [
                {"id": str(seed["unit"].id), "x": 50.0, "y": 60.0},
                {"id": str(uuid4()), "x": 1.0, "y": 2.0},
            ]
        },
        headers=_auth(seed["admin"]),
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"updated": 1}


def test_bulk_positions_empty_list(client: TestClient, seed: dict) -> None:
    r = client.patch(
        f"/organizations/{seed['own_org'].id}/nodes/positions",
        json={"positions": []},
        headers=_auth(seed["admin"]),
    )
    assert r.status_code == 200
    assert r.json() == {"updated": 0}
