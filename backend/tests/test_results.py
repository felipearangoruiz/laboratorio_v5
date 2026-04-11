from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.models
from app.core.security import create_access_token, hash_password
from app.db import get_session
from app.main import app
from app.models.interview import Interview
from app.models.member import Member, MemberTokenStatus
from app.models.organization import Organization
from app.models.user import User, UserRole


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


def _seed_base(session: Session) -> tuple[User, Organization]:
    organization = Organization(name="Org Diagnostico", description="", sector="tech")
    session.add(organization)
    session.commit()
    session.refresh(organization)

    admin = User(
        email="admin@test.com",
        hashed_password=hash_password("secret"),
        role=UserRole.ADMIN,
        organization_id=organization.id,
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)

    organization.admin_id = admin.id
    session.add(organization)
    session.commit()

    return admin, organization


class TestResultsRouter:
    @staticmethod
    def session_fixture() -> Generator[Session, None, None]:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(engine)
        with Session(engine) as db_session:
            yield db_session

    @staticmethod
    def client_fixture(session: Session) -> Generator[TestClient, None, None]:
        def override_get_session() -> Generator[Session, None, None]:
            yield session

        app.dependency_overrides[get_session] = override_get_session
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()


def test_trigger_resultado_falla_si_no_hay_entrevistas_completadas() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        admin, organization = _seed_base(session)

        def override_get_session() -> Generator[Session, None, None]:
            yield session

        app.dependency_overrides[get_session] = override_get_session
        with TestClient(app) as client:
            response = client.post(
                f"/organizations/{organization.id}/results/trigger",
                headers=auth_headers(admin),
            )

        app.dependency_overrides.clear()

        assert response.status_code == 400
        assert response.json()["detail"] == "No hay entrevistas completadas para generar diagnóstico"


def test_trigger_resultado_crea_job_y_processing_result() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        admin, organization = _seed_base(session)
        member = Member(
            organization_id=organization.id,
            name="Miembro 1",
            role_label="Analista",
            interview_token="token-1",
            token_status=MemberTokenStatus.COMPLETED,
        )
        session.add(member)
        session.commit()
        session.refresh(member)

        interview = Interview(
            member_id=member.id,
            organization_id=organization.id,
            group_id=None,
            data={
                "q01": "Las decisiones importantes se aprueban por una sola persona.",
                "q04": "Hay demoras y bloqueos frecuentes entre áreas.",
                "q07": "Las reglas formales no siempre se siguen.",
            },
            submitted_at=datetime.now(timezone.utc),
            schema_version=1,
        )
        session.add(interview)
        session.commit()

        def override_get_session() -> Generator[Session, None, None]:
            yield session

        app.dependency_overrides[get_session] = override_get_session
        with TestClient(app) as client:
            response = client.post(
                f"/organizations/{organization.id}/results/trigger",
                headers=auth_headers(admin),
            )

            latest_result = client.get(
                f"/organizations/{organization.id}/results/latest",
                headers=auth_headers(admin),
            )
            latest_job = client.get(
                f"/organizations/{organization.id}/results/status/latest",
                headers=auth_headers(admin),
            )

        app.dependency_overrides.clear()

        assert response.status_code == 201, response.text
        body = response.json()
        assert body["status"] == "completed"

        assert latest_result.status_code == 200
        result_body = latest_result.json()
        assert result_body["type"] == "ciego"
        assert "resumen_ejecutivo" in result_body["result"]

        assert latest_job.status_code == 200
        job_body = latest_job.json()
        assert job_body["status"] == "completed"
