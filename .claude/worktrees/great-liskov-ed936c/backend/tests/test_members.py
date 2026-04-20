from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import app.models
from app.core.security import create_access_token, hash_password
from app.db import get_session
from app.main import app
from app.models.group import Group
from app.models.member import Member
from app.models.organization import Organization
from app.models.user import User, UserRole


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
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
    superadmin = User(
        email="superadmin@test.com",
        hashed_password=hash_password("secret"),
        role=UserRole.SUPERADMIN,
        organization_id=own_org.id,
    )
    session.add(admin)
    session.add(other_admin)
    session.add(superadmin)
    session.commit()

    own_group = Group(organization_id=own_org.id, name="g-own", description="")
    own_group_2 = Group(organization_id=own_org.id, name="g-own-2", description="")
    other_group = Group(organization_id=other_org.id, name="g-other", description="")
    session.add(own_group)
    session.add(own_group_2)
    session.add(other_group)
    session.commit()
    session.refresh(own_group)
    session.refresh(own_group_2)
    session.refresh(other_group)

    return {
        "admin": admin,
        "other_admin": other_admin,
        "superadmin": superadmin,
        "own_org": own_org,
        "other_org": other_org,
        "own_group": own_group,
        "own_group_2": own_group_2,
        "other_group": other_group,
    }


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


def create_member(
    client: TestClient,
    user: User,
    organization_id: str,
    name: str,
    group_id: str | None = None,
) -> dict:
    payload = {
        "organization_id": organization_id,
        "name": name,
        "role_label": "analyst",
    }
    if group_id is not None:
        payload["group_id"] = group_id

    response = client.post("/members", json=payload, headers=auth_headers(user))
    assert response.status_code == 201, response.text
    return response.json()


def test_crear_miembro_genera_interview_token(client: TestClient, seeded_data: dict) -> None:
    member = create_member(
        client,
        seeded_data["admin"],
        str(seeded_data["own_org"].id),
        "Member 1",
        str(seeded_data["own_group"].id),
    )

    assert member["interview_token"]
    assert len(member["interview_token"]) >= 20


def test_token_status_inicia_en_pending(client: TestClient, seeded_data: dict) -> None:
    member = create_member(
        client,
        seeded_data["admin"],
        str(seeded_data["own_org"].id),
        "Member 1",
    )

    assert member["token_status"] == "pending"


def test_no_permitir_asignar_miembro_a_grupo_de_otra_organizacion(
    client: TestClient, seeded_data: dict
) -> None:
    response = client.post(
        "/members",
        json={
            "organization_id": str(seeded_data["own_org"].id),
            "name": "Invalid Group",
            "role_label": "analyst",
            "group_id": str(seeded_data["other_group"].id),
        },
        headers=auth_headers(seeded_data["admin"]),
    )

    assert response.status_code == 400


def test_get_organization_members_lista_solo_miembros_correctos(
    client: TestClient, seeded_data: dict
) -> None:
    own_org_id = str(seeded_data["own_org"].id)
    other_org_id = str(seeded_data["other_org"].id)

    create_member(client, seeded_data["admin"], own_org_id, "Own Member")
    create_member(client, seeded_data["superadmin"], other_org_id, "Other Member")

    response = client.get(
        f"/organizations/{own_org_id}/members",
        headers=auth_headers(seeded_data["admin"]),
    )

    assert response.status_code == 200
    members = response.json()
    assert all(member["organization_id"] == own_org_id for member in members)


def test_get_group_members_lista_miembros_del_grupo(
    client: TestClient, seeded_data: dict
) -> None:
    group_id = str(seeded_data["own_group"].id)
    org_id = str(seeded_data["own_org"].id)
    create_member(client, seeded_data["admin"], org_id, "M1", group_id)
    create_member(client, seeded_data["admin"], org_id, "M2", group_id)

    response = client.get(f"/groups/{group_id}/members", headers=auth_headers(seeded_data["admin"]))

    assert response.status_code == 200
    members = response.json()
    assert len(members) == 2
    assert all(member["group_id"] == group_id for member in members)


def test_patch_member_group_mueve_correctamente_al_miembro(
    client: TestClient, seeded_data: dict
) -> None:
    org_id = str(seeded_data["own_org"].id)
    member = create_member(
        client,
        seeded_data["admin"],
        org_id,
        "Movible",
        str(seeded_data["own_group"].id),
    )

    response = client.patch(
        f"/members/{member['id']}/group",
        json={"group_id": str(seeded_data["own_group_2"].id)},
        headers=auth_headers(seeded_data["admin"]),
    )

    assert response.status_code == 200
    assert response.json()["group_id"] == str(seeded_data["own_group_2"].id)


def test_admin_no_puede_tocar_miembros_de_otra_organizacion(
    client: TestClient, seeded_data: dict
) -> None:
    other_member = create_member(
        client,
        seeded_data["superadmin"],
        str(seeded_data["other_org"].id),
        "Other Member",
        str(seeded_data["other_group"].id),
    )

    response = client.delete(
        f"/members/{other_member['id']}",
        headers=auth_headers(seeded_data["admin"]),
    )

    assert response.status_code == 403


def test_no_permitir_borrar_grupo_con_miembros_asociados(
    client: TestClient, seeded_data: dict
) -> None:
    org_id = str(seeded_data["own_org"].id)
    create_member(
        client,
        seeded_data["admin"],
        org_id,
        "Assigned Member",
        str(seeded_data["own_group"].id),
    )

    response = client.delete(
        f"/groups/{seeded_data['own_group'].id}",
        headers=auth_headers(seeded_data["admin"]),
    )

    assert response.status_code == 400


def test_mover_miembro_a_grupo_valido_funciona(client: TestClient, seeded_data: dict) -> None:
    org_id = str(seeded_data["own_org"].id)
    member = create_member(
        client,
        seeded_data["admin"],
        org_id,
        "Movible",
        str(seeded_data["own_group"].id),
    )

    response = client.patch(
        f"/members/{member['id']}/group",
        json={"group_id": str(seeded_data["own_group_2"].id)},
        headers=auth_headers(seeded_data["admin"]),
    )

    assert response.status_code == 200


def test_mover_miembro_a_grupo_de_otra_organizacion_falla(
    client: TestClient, seeded_data: dict
) -> None:
    org_id = str(seeded_data["own_org"].id)
    member = create_member(
        client,
        seeded_data["admin"],
        org_id,
        "Movible",
        str(seeded_data["own_group"].id),
    )

    response = client.patch(
        f"/members/{member['id']}/group",
        json={"group_id": str(seeded_data["other_group"].id)},
        headers=auth_headers(seeded_data["admin"]),
    )

    assert response.status_code == 400


def test_interview_token_es_unico(client: TestClient, session: Session, seeded_data: dict) -> None:
    org_id = str(seeded_data["own_org"].id)
    create_member(client, seeded_data["admin"], org_id, "M1")
    create_member(client, seeded_data["admin"], org_id, "M2")

    tokens = [member.interview_token for member in session.exec(select(Member)).all()]
    assert len(tokens) == len(set(tokens))
