"""Sprint 2.B Commit 6a — Tests de /nodes/{id}/documents.

Valida:
  1. Happy path upload/list/delete.
  2. Cross-org 403 (user de orgA no puede tocar nodes de orgB).
  3. Invariante DB: INSERT con organization_id != node.organization_id
     debe fallar por el trigger fn_check_document_node_same_org.
"""
from __future__ import annotations

import io
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import DatabaseError, IntegrityError
from sqlmodel import Session

from app.routers import documents as documents_router

from app.core.security import create_access_token, hash_password
from app.models.document import Document, DocType
from app.models.node import Node, NodeType
from app.models.organization import Organization
from app.models.user import User, UserRole


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


@pytest.fixture(autouse=True)
def _tmp_upload_root(tmp_path, monkeypatch):
    """UPLOAD_ROOT por defecto es /app/uploads (Docker). En tests locales
    no podemos escribir ahí; redirigimos a tmp_path."""
    monkeypatch.setattr(documents_router, "UPLOAD_ROOT", str(tmp_path))


@pytest.fixture
def seeded(session: Session) -> dict:
    org_a = Organization(name="OrgADocs", admin_id=None)
    org_b = Organization(name="OrgBDocs", admin_id=None)
    session.add(org_a)
    session.add(org_b)
    session.flush()

    admin_a = User(
        email="admin-a-docs@test.com",
        hashed_password=hash_password("secret"),
        role=UserRole.ADMIN,
        organization_id=org_a.id,
    )
    admin_b = User(
        email="admin-b-docs@test.com",
        hashed_password=hash_password("secret"),
        role=UserRole.ADMIN,
        organization_id=org_b.id,
    )
    session.add(admin_a)
    session.add(admin_b)
    session.flush()

    node_a = Node(
        organization_id=org_a.id,
        type=NodeType.UNIT,
        name="UnitA",
        position_x=0.0,
        position_y=0.0,
        attrs={},
    )
    node_b = Node(
        organization_id=org_b.id,
        type=NodeType.UNIT,
        name="UnitB",
        position_x=0.0,
        position_y=0.0,
        attrs={},
    )
    session.add(node_a)
    session.add(node_b)
    session.commit()
    session.refresh(node_a)
    session.refresh(node_b)
    return {
        "org_a": org_a,
        "org_b": org_b,
        "admin_a": admin_a,
        "admin_b": admin_b,
        "node_a": node_a,
        "node_b": node_b,
    }


def test_node_document_upload_list_delete_happy_path(
    client: TestClient, seeded: dict
) -> None:
    admin_a = seeded["admin_a"]
    node_a = seeded["node_a"]

    # Upload
    file_bytes = b"contenido del archivo de prueba"
    r = client.post(
        f"/nodes/{node_a.id}/documents",
        files={"file": ("acta.txt", io.BytesIO(file_bytes), "text/plain")},
        data={"label": "Acta de constitución", "doc_type": "other"},
        headers=_auth(admin_a),
    )
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["label"] == "Acta de constitución"
    assert doc["node_id"] == str(node_a.id)
    assert doc["organization_id"] == str(node_a.organization_id)
    assert doc["doc_type"] == "other"
    doc_id = doc["id"]

    # List
    r = client.get(f"/nodes/{node_a.id}/documents", headers=_auth(admin_a))
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 1
    assert items[0]["id"] == doc_id

    # Delete
    r = client.delete(
        f"/nodes/{node_a.id}/documents/{doc_id}",
        headers=_auth(admin_a),
    )
    assert r.status_code == 204, r.text

    # Verify empty after delete
    r = client.get(f"/nodes/{node_a.id}/documents", headers=_auth(admin_a))
    assert r.status_code == 200
    assert r.json() == []


def test_node_document_cross_org_blocked(
    client: TestClient, seeded: dict
) -> None:
    """admin de orgA no puede subir/listar/borrar en node de orgB."""
    admin_a = seeded["admin_a"]
    node_b = seeded["node_b"]

    # Upload cross-org → 403
    r = client.post(
        f"/nodes/{node_b.id}/documents",
        files={"file": ("x.txt", io.BytesIO(b"x"), "text/plain")},
        data={"label": "Intruso", "doc_type": "other"},
        headers=_auth(admin_a),
    )
    assert r.status_code == 403, r.text

    # List cross-org → 403
    r = client.get(f"/nodes/{node_b.id}/documents", headers=_auth(admin_a))
    assert r.status_code == 403


def test_node_document_db_invariant_triggers(
    session: Session, seeded: dict
) -> None:
    """INSERT directo con organization_id mismatch → IntegrityError por trigger."""
    org_a = seeded["org_a"]
    node_b = seeded["node_b"]  # pertenece a org_b

    bad_doc = Document(
        id=uuid4(),
        organization_id=org_a.id,   # org_a
        node_id=node_b.id,          # pero el node es de org_b
        label="invalid",
        doc_type=DocType.OTHER.value,
        filename="x.txt",
        filepath="/tmp/x.txt",
    )
    session.add(bad_doc)
    # El trigger RAISE EXCEPTION llega como DatabaseError (ProgrammingError
    # subclass). IntegrityError es subclass de DatabaseError también.
    with pytest.raises(DatabaseError, match="must match nodes.organization_id"):
        session.flush()
    session.rollback()
