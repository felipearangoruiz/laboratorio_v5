from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, hash_password
from app.models.organization import Organization
from app.models.user import User, UserRole


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
        email="superadmin@test.com",
        hashed_password=hash_password("secret"),
        role=UserRole.SUPERADMIN,
        organization_id=own_org.id,
    )
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
    admin_without_org = User(
        email="admin-without-org@test.com",
        hashed_password=hash_password("secret"),
        role=UserRole.ADMIN,
        organization_id=None,
    )
    session.add(superadmin)
    session.add(admin)
    session.add(other_admin)
    session.add(admin_without_org)
    session.commit()
    session.refresh(superadmin)
    session.refresh(admin)
    session.refresh(other_admin)
    session.refresh(admin_without_org)

    own_org.admin_id = admin.id
    other_org.admin_id = other_admin.id
    session.add(own_org)
    session.add(other_org)
    session.commit()

    return {
        "superadmin": superadmin,
        "admin": admin,
        "other_admin": other_admin,
        "admin_without_org": admin_without_org,
        "own_org": own_org,
        "other_org": other_org,
    }


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


def test_superadmin_crea_organizacion(client: TestClient, seeded_data: dict) -> None:
    response = client.post(
        "/organizations",
        json={"name": "Nueva Org", "description": "desc", "sector": "fintech"},
        headers=auth_headers(seeded_data["superadmin"]),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Nueva Org"


def test_admin_sin_organizacion_crea_organizacion_y_queda_vinculado(
    client: TestClient, session: Session, seeded_data: dict
) -> None:
    admin_without_org = seeded_data["admin_without_org"]
    response = client.post(
        "/organizations",
        json={"name": "Mi Org", "description": "desc", "sector": "legal"},
        headers=auth_headers(admin_without_org),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Mi Org"
    assert body["admin_id"] == str(admin_without_org.id)

    session.refresh(admin_without_org)
    assert admin_without_org.organization_id is not None
    assert str(admin_without_org.organization_id) == body["id"]


def test_admin_sin_organizacion_no_puede_crear_para_otro_admin(
    client: TestClient, seeded_data: dict
) -> None:
    response = client.post(
        "/organizations",
        json={
            "name": "Intento inválido",
            "description": "desc",
            "sector": "legal",
            "admin_id": str(seeded_data["other_admin"].id),
        },
        headers=auth_headers(seeded_data["admin_without_org"]),
    )

    assert response.status_code == 403


def test_admin_con_organizacion_no_puede_crear_otra(
    client: TestClient, seeded_data: dict
) -> None:
    response = client.post(
        "/organizations",
        json={"name": "Otra Org", "description": "desc", "sector": "retail"},
        headers=auth_headers(seeded_data["admin"]),
    )

    assert response.status_code == 403


def test_superadmin_lista_organizaciones(client: TestClient, seeded_data: dict) -> None:
    response = client.get(
        "/organizations",
        headers=auth_headers(seeded_data["superadmin"]),
    )

    assert response.status_code == 200
    assert len(response.json()) >= 2


def test_admin_no_puede_listar_organizaciones(client: TestClient, seeded_data: dict) -> None:
    response = client.get(
        "/organizations",
        headers=auth_headers(seeded_data["admin"]),
    )

    assert response.status_code == 403


def test_admin_puede_ver_su_propia_organizacion(client: TestClient, seeded_data: dict) -> None:
    response = client.get(
        f"/organizations/{seeded_data['own_org'].id}",
        headers=auth_headers(seeded_data["admin"]),
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(seeded_data["own_org"].id)


def test_admin_no_puede_ver_organizacion_ajena(client: TestClient, seeded_data: dict) -> None:
    response = client.get(
        f"/organizations/{seeded_data['other_org'].id}",
        headers=auth_headers(seeded_data["admin"]),
    )

    assert response.status_code == 403


def test_admin_puede_editar_su_organizacion(client: TestClient, seeded_data: dict) -> None:
    response = client.patch(
        f"/organizations/{seeded_data['own_org'].id}",
        json={"description": "actualizada"},
        headers=auth_headers(seeded_data["admin"]),
    )

    assert response.status_code == 200
    assert response.json()["description"] == "actualizada"


def test_admin_no_puede_editar_organizacion_ajena(client: TestClient, seeded_data: dict) -> None:
    response = client.patch(
        f"/organizations/{seeded_data['other_org'].id}",
        json={"description": "no"},
        headers=auth_headers(seeded_data["admin"]),
    )

    assert response.status_code == 403


def test_admin_no_puede_eliminar_organizaciones(client: TestClient, seeded_data: dict) -> None:
    response = client.delete(
        f"/organizations/{seeded_data['own_org'].id}",
        headers=auth_headers(seeded_data["admin"]),
    )

    assert response.status_code == 403
