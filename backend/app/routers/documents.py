"""Documentos institucionales adjuntos a una organización."""
from __future__ import annotations

import os
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlmodel import Session, select

from app.core.dependencies import get_current_user
from app.db import get_session
from app.models.document import Document, DocumentRead, DocType
from app.models.node import Node
from app.models.user import User, UserRole

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
UPLOAD_ROOT = "/app/uploads"


def _can_access_org(user: User, org_id: UUID) -> bool:
    return user.role == UserRole.SUPERADMIN or user.organization_id == org_id


def _org_upload_dir(org_id: UUID) -> str:
    path = os.path.join(UPLOAD_ROOT, str(org_id))
    os.makedirs(path, exist_ok=True)
    return path


def _node_upload_dir(org_id: UUID, node_id: UUID) -> str:
    path = os.path.join(UPLOAD_ROOT, str(org_id), "nodes", str(node_id))
    os.makedirs(path, exist_ok=True)
    return path


@router.post(
    "/organizations/{org_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    tags=["documents"],
)
async def upload_document(
    org_id: UUID,
    file: Annotated[UploadFile, File(description="PDF, DOCX o TXT — máximo 20 MB")],
    label: Annotated[str, Form(description="Nombre descriptivo del documento")],
    doc_type: Annotated[str, Form(description="'institutional' o 'other'")] = DocType.INSTITUTIONAL.value,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    session: Session = Depends(get_session),
) -> DocumentRead:
    if not _can_access_org(current_user, org_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    # Validate doc_type
    if doc_type not in {DocType.INSTITUTIONAL.value, DocType.OTHER.value}:
        raise HTTPException(
            status_code=400,
            detail=f"doc_type debe ser '{DocType.INSTITUTIONAL.value}' o '{DocType.OTHER.value}'",
        )

    # Validate file extension
    original_filename = file.filename or "document"
    ext = os.path.splitext(original_filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extensión no permitida. Usa: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Read and size-check
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"El archivo supera el límite de {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    # Save to disk
    upload_dir = _org_upload_dir(org_id)
    # Use Document UUID as filename prefix to avoid collisions
    from uuid import uuid4
    doc_id = uuid4()
    safe_filename = f"{doc_id.hex}{ext}"
    filepath = os.path.join(upload_dir, safe_filename)

    with open(filepath, "wb") as f:
        f.write(content)

    doc = Document(
        id=doc_id,
        organization_id=org_id,
        label=label.strip(),
        doc_type=doc_type,
        filename=original_filename,
        filepath=filepath,
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return DocumentRead.model_validate(doc)


@router.get(
    "/organizations/{org_id}/documents",
    response_model=list[DocumentRead],
    tags=["documents"],
)
def list_documents(
    org_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> list[DocumentRead]:
    if not _can_access_org(current_user, org_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    docs = session.exec(
        select(Document)
        .where(Document.organization_id == org_id)
        .order_by(Document.created_at.desc())
    ).all()
    return [DocumentRead.model_validate(d) for d in docs]


@router.delete(
    "/organizations/{org_id}/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["documents"],
)
def delete_document(
    org_id: UUID,
    doc_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
):
    if not _can_access_org(current_user, org_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    doc = session.get(Document, doc_id)
    if not doc or doc.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove file from disk (best-effort — don't fail if already gone)
    try:
        if os.path.isfile(doc.filepath):
            os.remove(doc.filepath)
    except OSError:
        pass

    session.delete(doc)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================
# Sprint 2.B Commit 6a — Documentos por Node (shim endpoints)
# ============================================================
# Los documentos institucionales siguen viviendo bajo
# /organizations/{org_id}/documents (node_id IS NULL). Los
# endpoints siguientes permiten asociar documentos a un Node
# específico; el trigger PL/pgSQL fn_check_document_node_same_org
# garantiza que documents.organization_id coincida con la org del
# Node referenciado.


@router.post(
    "/nodes/{node_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    tags=["documents"],
)
async def upload_node_document(
    node_id: UUID,
    file: Annotated[UploadFile, File(description="PDF, DOCX o TXT — máximo 20 MB")],
    label: Annotated[str, Form(description="Nombre descriptivo del documento")],
    doc_type: Annotated[str, Form(description="'institutional' o 'other'")] = DocType.OTHER.value,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    session: Session = Depends(get_session),
) -> DocumentRead:
    node = session.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if not _can_access_org(current_user, node.organization_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    if doc_type not in {DocType.INSTITUTIONAL.value, DocType.OTHER.value}:
        raise HTTPException(
            status_code=400,
            detail=f"doc_type debe ser '{DocType.INSTITUTIONAL.value}' o '{DocType.OTHER.value}'",
        )

    original_filename = file.filename or "document"
    ext = os.path.splitext(original_filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extensión no permitida. Usa: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"El archivo supera el límite de {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    upload_dir = _node_upload_dir(node.organization_id, node_id)
    from uuid import uuid4

    doc_id = uuid4()
    safe_filename = f"{doc_id.hex}{ext}"
    filepath = os.path.join(upload_dir, safe_filename)

    with open(filepath, "wb") as f:
        f.write(content)

    doc = Document(
        id=doc_id,
        organization_id=node.organization_id,
        node_id=node_id,
        label=label.strip(),
        doc_type=doc_type,
        filename=original_filename,
        filepath=filepath,
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return DocumentRead.model_validate(doc)


@router.get(
    "/nodes/{node_id}/documents",
    response_model=list[DocumentRead],
    tags=["documents"],
)
def list_node_documents(
    node_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> list[DocumentRead]:
    node = session.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if not _can_access_org(current_user, node.organization_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    docs = session.exec(
        select(Document)
        .where(Document.node_id == node_id)
        .order_by(Document.created_at.desc())
    ).all()
    return [DocumentRead.model_validate(d) for d in docs]


@router.delete(
    "/nodes/{node_id}/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["documents"],
)
def delete_node_document(
    node_id: UUID,
    doc_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
):
    node = session.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if not _can_access_org(current_user, node.organization_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    doc = session.get(Document, doc_id)
    if not doc or doc.node_id != node_id:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        if os.path.isfile(doc.filepath):
            os.remove(doc.filepath)
    except OSError:
        pass

    session.delete(doc)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
