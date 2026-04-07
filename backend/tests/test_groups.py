from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from app.core.security import create_access_token, hash_password
from app.db import get_session
from app.main import app
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
def seeded_data(session: Session) -> dict[str, User | Organization]:
    own_org = Organization(name="Org Admin", description="", sector="tech")
    other_org = Organization(name="Org Other", description="", sector="retail")
    session.add(own_org)
    session.add(other_org)
    session.commit()
    session.refresh(own_org)
    session.refresh(other_org)

    superadmin = User(
        email="superadmin.groups@test.com",
        hashed_password=hash_password("secret"),
        role=UserRole.SUPERADMIN,
        organization_id=own_org.id,
    )
    admin = User(
        email="admin.groups@test.com",
        hashed_password=hash_password("secret"),
        role=UserRole.ADMIN,
        organization_id=own_org.id,
    )
    other_admin = User(
        email="other-admin.groups@test.com",
        hashed_password=hash_password("secret"),
        role=UserRole.ADMIN,
        organization_id=other_org.id,
    )
    session.add(superadmin)
    session.add(admin)
    session.add(other_admin)
    session.commit()
    session.refresh(superadmin)
    session.refresh(admin)
    session.refresh(other_admin)

    return {
        "superadmin": superadmin,
        "admin": admin,
        "other_admin": other_admin,
        "own_org": own_org,
        "other_org": other_org,
    }


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


def _create_group(
    client: TestClient,
    user: User,
    *,
    organization_id: str,
    name: str,
    parent_group_id: str | None = None,
    is_default: bool = False,
) -> dict:
    payload = {
        "organization_id": organization_id,
        "name": name,
        "description": "",
        "tarea_general": "",
        "is_default": is_default,
    }
    if parent_group_id is not None:
        payload["parent_group_id"] = parent_group_id

    response = client.post("/groups", json=payload, headers=auth_headers(user))
    assert response.status_code == 201
    return response.json()


def test_crear_jerarquia_3_niveles(client: TestClient, seeded_data: dict) -> None:
    org_id = str(seeded_data["own_org"].id)
    raiz = _create_group(client, seeded_data["admin"], organization_id=org_id, name="A")
    hijo = _create_group(
        client,
        seeded_data["admin"],
        organization_id=org_id,
        name="B",
        parent_group_id=raiz["id"],
    )
    nieto = _create_group(
        client,
        seeded_data["admin"],
        organization_id=org_id,
        name="C",
        parent_group_id=hijo["id"],
    )

    assert hijo["parent_group_id"] == raiz["id"]
    assert nieto["parent_group_id"] == hijo["id"]


def test_impide_padre_de_otra_organizacion(client: TestClient, seeded_data: dict) -> None:
    otro = _create_group(
        client,
        seeded_data["other_admin"],
        organization_id=str(seeded_data["other_org"].id),
        name="Padre Ajeno",
    )

    response = client.post(
        "/groups",
        json={
            "organization_id": str(seeded_data["own_org"].id),
            "name": "Hijo",
            "parent_group_id": otro["id"],
        },
        headers=auth_headers(seeded_data["superadmin"]),
    )

    assert response.status_code == 400


def test_impide_eliminar_grupo_con_hijos(client: TestClient, seeded_data: dict) -> None:
    org_id = str(seeded_data["own_org"].id)
    padre = _create_group(client, seeded_data["admin"], organization_id=org_id, name="Padre")
    _create_group(
        client,
        seeded_data["admin"],
        organization_id=org_id,
        name="Hijo",
        parent_group_id=padre["id"],
    )

    response = client.delete(f"/groups/{padre['id']}", headers=auth_headers(seeded_data["admin"]))

    assert response.status_code == 400


def test_impide_eliminar_grupo_default(client: TestClient, seeded_data: dict) -> None:
    group = _create_group(
        client,
        seeded_data["admin"],
        organization_id=str(seeded_data["own_org"].id),
        name="Default",
        is_default=True,
    )

    response = client.delete(f"/groups/{group['id']}", headers=auth_headers(seeded_data["admin"]))

    assert response.status_code == 400


def test_tree_devuelve_estructura_anidada(client: TestClient, seeded_data: dict) -> None:
    org_id = str(seeded_data["own_org"].id)
    root = _create_group(client, seeded_data["admin"], organization_id=org_id, name="Root")
    child = _create_group(
        client,
        seeded_data["admin"],
        organization_id=org_id,
        name="Child",
        parent_group_id=root["id"],
    )
    _create_group(
        client,
        seeded_data["admin"],
        organization_id=org_id,
        name="Grandchild",
        parent_group_id=child["id"],
    )

    response = client.get(
        f"/organizations/{seeded_data['own_org'].id}/groups/tree",
        headers=auth_headers(seeded_data["admin"]),
    )

    assert response.status_code == 200
    tree = response.json()
    assert len(tree) == 1
    assert tree[0]["id"] == root["id"]
    assert len(tree[0]["children"]) == 1
    assert tree[0]["children"][0]["id"] == child["id"]
    assert len(tree[0]["children"][0]["children"]) == 1


def test_admin_no_puede_tocar_grupos_de_otra_org(client: TestClient, seeded_data: dict) -> None:
    group = _create_group(
        client,
        seeded_data["other_admin"],
        organization_id=str(seeded_data["other_org"].id),
        name="Ajeno",
    )

    response = client.patch(
        f"/groups/{group['id']}",
        json={"name": "No permitido"},
        headers=auth_headers(seeded_data["admin"]),
    )

    assert response.status_code == 403
