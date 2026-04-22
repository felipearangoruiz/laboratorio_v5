"""Sprint 2.B — Test de preservación de claves custom en attrs.

Valida que los mirror helpers `_build_unit_attrs` y `_build_person_attrs`
preserven las claves no-legacy (p. ej. `admin_notes`) escritas por el
frontend vía PATCH /nodes cuando un PATCH legacy (/groups, /members)
reconstruye los attrs del Node espejo.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, hash_password
from app.models.group import Group
from app.models.organization import Organization
from app.models.user import User, UserRole


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


@pytest.fixture
def seeded(session: Session) -> dict:
    org = Organization(name="OrgAdminNotes", admin_id=None)
    session.add(org)
    session.flush()

    admin = User(
        email="admin-notes@test.com",
        hashed_password=hash_password("secret"),
        role=UserRole.ADMIN,
        organization_id=org.id,
    )
    session.add(admin)
    session.flush()

    root = Group(
        organization_id=org.id,
        name="RaízNotes",
        node_type="area",
        position_x=0.0,
        position_y=0.0,
    )
    session.add(root)
    session.commit()
    session.refresh(root)
    return {"org": org, "admin": admin, "root": root}


def test_admin_notes_preservado_tras_patch_group(
    client: TestClient, session: Session, seeded: dict
) -> None:
    """Escenario A (unit/group): admin_notes seteado vía PATCH /nodes se
    preserva cuando un PATCH /groups reconstruye los attrs del Node espejo."""
    admin = seeded["admin"]
    org = seeded["org"]

    # 1) POST /groups crea group + Node(unit) espejo.
    r = client.post(
        "/groups",
        json={
            "organization_id": str(org.id),
            "name": "UnitConNotes",
            "description": "desc inicial",
            "position_x": 10.0,
            "position_y": 20.0,
        },
        headers=_auth(admin),
    )
    assert r.status_code == 201, r.text
    gid = r.json()["id"]

    # 2) PATCH /nodes/{id} agrega admin_notes en attrs.
    r = client.patch(
        f"/nodes/{gid}",
        json={"attrs": {"admin_notes": "nota-secreta-unit"}},
        headers=_auth(admin),
    )
    assert r.status_code == 200, r.text
    session.expire_all()

    # 3) PATCH /groups/{id} cambia name → fuerza rebuild de attrs.
    r = client.patch(
        f"/groups/{gid}",
        json={"name": "UnitRenombrada"},
        headers=_auth(admin),
    )
    assert r.status_code == 200, r.text

    # 4) GET /nodes/{id} → admin_notes debe seguir presente.
    r = client.get(f"/nodes/{gid}", headers=_auth(admin))
    assert r.status_code == 200, r.text
    attrs = r.json()["attrs"]
    assert attrs.get("admin_notes") == "nota-secreta-unit"
    # Y los legacy siguen coherentes con el PATCH:
    assert r.json()["name"] == "UnitRenombrada"


def test_admin_notes_preservado_tras_patch_member(
    client: TestClient, session: Session, seeded: dict
) -> None:
    """Escenario B (person/member): admin_notes seteado vía PATCH /nodes se
    preserva cuando un PATCH /members reconstruye los attrs del Node espejo."""
    admin = seeded["admin"]
    org = seeded["org"]
    root = seeded["root"]

    # Asegurar que el Node(unit) raíz espejo exista (normalmente lo crea
    # POST /groups; aquí lo creamos si falta).
    from app.models.node import Node, NodeType

    if session.get(Node, root.id) is None:
        session.add(
            Node(
                id=root.id,
                organization_id=org.id,
                type=NodeType.UNIT,
                name=root.name,
                position_x=root.position_x,
                position_y=root.position_y,
                attrs={},
            )
        )
        session.commit()

    # 1) POST /members crea member + Node(person) espejo.
    r = client.post(
        "/members",
        json={
            "organization_id": str(org.id),
            "name": "PersonaNotes",
            "role_label": "rol-inicial",
            "group_id": str(root.id),
        },
        headers=_auth(admin),
    )
    assert r.status_code == 201, r.text
    mid = r.json()["id"]

    # 2) PATCH /nodes/{id} agrega admin_notes en attrs.
    r = client.patch(
        f"/nodes/{mid}",
        json={"attrs": {"admin_notes": "nota-secreta-person"}},
        headers=_auth(admin),
    )
    assert r.status_code == 200, r.text
    session.expire_all()

    # 3) PATCH /members/{id} cambia name → fuerza rebuild de attrs.
    r = client.patch(
        f"/members/{mid}",
        json={"name": "PersonaRenombrada"},
        headers=_auth(admin),
    )
    assert r.status_code == 200, r.text

    # 4) GET /nodes/{id} → admin_notes debe seguir presente.
    r = client.get(f"/nodes/{mid}", headers=_auth(admin))
    assert r.status_code == 200, r.text
    attrs = r.json()["attrs"]
    assert attrs.get("admin_notes") == "nota-secreta-person"
    assert r.json()["name"] == "PersonaRenombrada"
    # Legacy sigue coherente:
    assert attrs.get("role_label") == "rol-inicial"
