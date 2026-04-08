from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

import app.models
from app.core.security import create_access_token, hash_password
from app.db import get_session
from app.main import app
from app.models.group import Group
from app.models.organization import Organization
from app.models.user import User, UserRole


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


@pytest.fixture
def client(session: Session) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_data(session: Session) -> dict[str, User | Organization | Group]:
    own_org = Organization(name="Org A", description="", sector="tech")
    other_org = Organization(name="Org B", description="", sector="retail")
    session.add(own_org)
    session.add(other_org)
    session.commit()
    session.refresh(own_org)
    session.refresh(other_org)

    admin = User(
        email="admin@test.com",
        hashed_password=hash_password("secret"),
        role=UserRole.ADMIN,
        organization_id=own_org.id,
    )
    other_admin = User(
        email="other-admin@test.com",
        hashed_password=hash_password("secret"),
        role=UserRole.ADMIN,
        organization_id=other_org.id,
    )
    session.add(admin)
    session.add(other_admin)
    session.commit()
    session.refresh(admin)
    session.refresh(other_admin)

    own_org.admin_id = admin.id
    other_org.admin_id = other_admin.id
    session.add(own_org)
    session.add(other_org)

    default_group = Group(
        organization_id=own_org.id,
        name="default",
        description="Grupo default",
        is_default=True,
    )
    other_org_group = Group(
        organization_id=other_org.id,
        name="externo",
        description="Grupo de otra org",
    )
    session.add(default_group)
    session.add(other_org_group)
    session.commit()
    session.refresh(default_group)
    session.refresh(other_org_group)

    return {
        "admin": admin,
        "other_admin": other_admin,
        "own_org": own_org,
        "other_org": other_org,
        "default_group": default_group,
        "other_org_group": other_org_group,
    }


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


def create_group(
    client: TestClient,
    user: User,
    name: str,
    parent_group_id: str | None = None,
) -> dict:
    payload = {
        "name": name,
        "description": f"{name} desc",
        "tarea_general": "tarea",
        "nivel_jerarquico": 1,
        "tipo_nivel": "nivel",
    }
    if parent_group_id:
        payload["parent_group_id"] = parent_group_id

    response = client.post("/groups", json=payload, headers=auth_headers(user))
    assert response.status_code == 201, response.text
    return response.json()


def test_crear_jerarquia_de_3_niveles(client: TestClient, seeded_data: dict) -> None:
    root = create_group(client, seeded_data["admin"], "Root")
    child = create_group(
        client,
        seeded_data["admin"],
        "Child",
        parent_group_id=root["id"],
    )
    grandchild = create_group(
        client,
        seeded_data["admin"],
        "GrandChild",
        parent_group_id=child["id"],
    )

    assert child["parent_group_id"] == root["id"]
    assert grandchild["parent_group_id"] == child["id"]


def test_impedir_parent_de_otra_organizacion(
    client: TestClient, seeded_data: dict
) -> None:
    response = client.post(
        "/groups",
        json={
            "name": "Invalid Parent",
            "description": "no",
            "tarea_general": "x",
            "parent_group_id": str(seeded_data["other_org_group"].id),
        },
        headers=auth_headers(seeded_data["admin"]),
    )

    assert response.status_code in {400, 403}


def test_impedir_eliminar_grupo_con_hijos(
    client: TestClient, seeded_data: dict
) -> None:
    parent = create_group(client, seeded_data["admin"], "Parent")
    create_group(
        client,
        seeded_data["admin"],
        "Child",
        parent_group_id=parent["id"],
    )

    response = client.delete(
        f"/groups/{parent['id']}",
        headers=auth_headers(seeded_data["admin"]),
    )

    assert response.status_code in {400, 409}


def test_impedir_eliminar_grupo_default(client: TestClient, seeded_data: dict) -> None:
    response = client.delete(
        f"/groups/{seeded_data['default_group'].id}",
        headers=auth_headers(seeded_data["admin"]),
    )

    assert response.status_code in {400, 403}


def test_endpoint_tree_devuelve_estructura_anidada(
    client: TestClient, seeded_data: dict
) -> None:
    root = create_group(client, seeded_data["admin"], "Root")
    child = create_group(
        client,
        seeded_data["admin"],
        "Child",
        parent_group_id=root["id"],
    )
    grandchild = create_group(
        client,
        seeded_data["admin"],
        "GrandChild",
        parent_group_id=child["id"],
    )

    response = client.get("/groups/tree", headers=auth_headers(seeded_data["admin"]))

    assert response.status_code == 200
    tree = response.json()
    assert isinstance(tree, list)
    root_node = next(node for node in tree if node["id"] == root["id"])
    assert len(root_node["children"]) >= 1
    child_node = next(node for node in root_node["children"] if node["id"] == child["id"])
    assert len(child_node["children"]) >= 1
    assert any(node["id"] == grandchild["id"] for node in child_node["children"])


def test_admin_no_puede_tocar_grupos_de_otra_organizacion(
    client: TestClient, seeded_data: dict
) -> None:
    response = client.patch(
        f"/groups/{seeded_data['other_org_group'].id}",
        json={"name": "hack attempt"},
        headers=auth_headers(seeded_data["admin"]),
    )

    assert response.status_code == 403
