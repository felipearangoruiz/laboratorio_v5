"""Infraestructura compartida de tests.

Arranca un contenedor Postgres real con `testcontainers` (una sola vez por
sesión de pytest), corre `alembic upgrade head` contra él, y expone fixtures
`session` y `client` que los tests consumen.

Motivo: los modelos Node/Edge/AssessmentCampaign/NodeState usan columnas
jsonb nativas de Postgres, incompatibles con SQLite. Usar Postgres real en
tests garantiza que las invariantes se validen contra el mismo motor que
producción.

Requisito operativo: Docker debe estar disponible (Docker Desktop, Colima
o equivalente). Si el daemon no responde, testcontainers falla al arrancar
y pytest reporta el error sin silenciarlo.

Compatibilidad con Colima: el contenedor Ryuk (reaper de testcontainers)
no arranca de forma fiable en Colima porque depende de un mount del socket
docker con semántica distinta a Docker Desktop. Se desactiva vía
`TESTCONTAINERS_RYUK_DISABLED=true`; el cleanup se hace por el context
manager de `PostgresContainer`. Además, si existe el socket de Colima y no
hay `DOCKER_HOST` exportado, lo seteamos automáticamente para que
`docker-py` lo encuentre.

Aislamiento entre tests: cada test corre dentro de una transacción outer
sobre una conexión dedicada, con un SAVEPOINT anidado (`join_transaction_mode
= "create_savepoint"`). Los `session.commit()` del test/app liberan el
savepoint y abren uno nuevo; el teardown hace rollback del outer y limpia
todo. Barato (~ms) y no requiere TRUNCATE.
"""
from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

# Debe setearse ANTES de importar testcontainers.
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
_colima_sock = os.path.expanduser("~/.colima/default/docker.sock")
if "DOCKER_HOST" not in os.environ and os.path.exists(_colima_sock):
    os.environ["DOCKER_HOST"] = f"unix://{_colima_sock}"

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Connection, Engine
from sqlmodel import Session
from testcontainers.postgres import PostgresContainer

import app.models  # noqa: F401  — registra metadata de SQLModel
from app.core.config import settings
from app.db import get_session
from app.main import app

_BACKEND_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def _postgres_url() -> Generator[str, None, None]:
    """Arranca Postgres 16 y corre alembic upgrade head una sola vez."""
    with PostgresContainer("postgres:16", driver="psycopg") as pg:
        url = pg.get_connection_url()
        # Sincroniza el settings global para que alembic/env.py lea la URL
        # del contenedor en lugar del Postgres de desarrollo.
        previous = settings.DATABASE_URL
        settings.DATABASE_URL = url
        try:
            cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
            cfg.set_main_option("script_location", str(_BACKEND_ROOT / "alembic"))
            command.upgrade(cfg, "head")
            yield url
        finally:
            settings.DATABASE_URL = previous


@pytest.fixture(scope="session")
def _engine(_postgres_url: str) -> Generator[Engine, None, None]:
    engine = create_engine(_postgres_url, future=True)
    yield engine
    engine.dispose()


@pytest.fixture
def session(_engine: Engine) -> Generator[Session, None, None]:
    """Sesión SQLModel aislada por test vía SAVEPOINT anidado."""
    connection: Connection = _engine.connect()
    outer = connection.begin()
    db_session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield db_session
    finally:
        db_session.close()
        outer.rollback()
        connection.close()


@pytest.fixture
def client(session: Session) -> Generator[TestClient, None, None]:
    """TestClient con get_session sobrescrito para usar la sesión del test."""

    def override_get_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
