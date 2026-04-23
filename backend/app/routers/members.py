"""COMPATIBILITY LAYER — Sprint 1.4

Este router es legacy. Cada operación de escritura se espeja sobre la
tabla nueva (`nodes` con `type="person"`) dentro de la misma transacción
para mantener los datos sincronizados durante la coexistencia del viejo
y el nuevo modelo.

Los endpoints están marcados `deprecated=True`. Los consumidores deben
migrar a /nodes, /edges, /node-states, /campaigns.

Eliminar este router cuando:
  - El frontend no llame a ningún endpoint legacy.
  - (Sprint 3 cerrado: el motor de análisis ya apunta a
    `node_analyses.node_id` / `group_analyses.node_id`, FKs a
    `nodes.id`; ver migración 20260423_0012.)

Política de espejado:
  - POST /members           → INSERT Member + INSERT Node (mismo UUID, person).
  - PATCH /members/{id}     → UPDATE Member + UPDATE Node (fallback: crea).
  - PATCH /members/{id}/group → mover parent_node_id en el Node espejo.
  - DELETE /members/{id}    → proteger contra NodeAnalyses referenciando
                              el UUID (409), luego DELETE Member +
                              soft-delete Node.

Nota de invariantes: invariante 3 de MODEL_PHILOSOPHY.md §8 exige que
person tenga parent_node_id NOT NULL. La API legacy permite `group_id=None`
para Members huérfanos. En ese caso creamos el Node person con
parent_node_id=None — el DB lo acepta (columna nullable) y documentamos
la excepción legacy en log. Un backfill futuro adoptará la unit default
de la organización.
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel import Session, select

from app.core.dependencies import get_current_user
from app.db import get_session
from app.models.group import Group
from app.models.member import Member, MemberRead, MemberTokenStatus
from app.models.node import Node, NodeType
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter()


class MemberCreate(BaseModel):
    organization_id: UUID
    name: str
    role_label: str = ""
    group_id: UUID | None = None


class MemberUpdate(BaseModel):
    name: str | None = None
    role_label: str | None = None
    group_id: UUID | None = None
    token_status: MemberTokenStatus | None = None


class MemberMoveGroup(BaseModel):
    group_id: UUID | None


def _can_access_org(user: User, organization_id: UUID) -> bool:
    return user.role == UserRole.SUPERADMIN or user.organization_id == organization_id


def _ensure_member_access(member: Member, user: User) -> None:
    if not _can_access_org(user, member.organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")


def _validate_group_assignment(
    session: Session,
    organization_id: UUID,
    group_id: UUID | None,
) -> None:
    if group_id is None:
        return

    group = session.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    if group.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group must belong to same organization",
        )


def _generate_unique_token(session: Session) -> str:
    for _ in range(10):
        token = secrets.token_urlsafe(24)
        exists = session.exec(select(Member).where(Member.interview_token == token)).first()
        if not exists:
            return token
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not generate token")


# ────────────── Mirror helpers (Member ↔ Node type=person) ──────────────

def _build_person_attrs(
    member: Member,
    prev_attrs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Metadata del Member sin columna directa en Node queda en attrs.

    Si se pasa `prev_attrs` (dict del Node espejo existente), se preservan
    las claves NO-legacy (p. ej. `admin_notes`) que el frontend escribe
    vía PATCH /nodes. Los campos legacy siempre se reemplazan con los
    valores actuales del Member.
    """
    attrs: dict[str, Any] = {
        "role_label": member.role_label or "",
        "interview_token": member.interview_token,
        "token_status": member.token_status.value,
    }
    # Member no tiene columna `email` en el modelo actual; si se agrega en
    # el futuro, aquí quedaría mapeado automáticamente.
    email = getattr(member, "email", None)
    if email:
        attrs["email"] = email
    if prev_attrs:
        for key, value in prev_attrs.items():
            if key not in attrs:
                attrs[key] = value
    return attrs


def _resolve_person_parent_node_id(
    session: Session,
    member: Member,
) -> UUID | None:
    """Devuelve el id del Node unit parent (garantizado por espejado de Groups).

    Si el Group referenciado no tiene Node espejo vivo (inconsistencia
    pre-1.4), loggea warning y retorna None; el Node person queda huérfano
    en lugar de rechazar la operación legacy.
    """
    if member.group_id is None:
        logger.info(
            "Member %s sin group_id; Node espejo queda con parent_node_id=None "
            "(permitido por compat legacy; invariante 3 se relaja).",
            member.id,
        )
        return None
    parent_node = session.get(Node, member.group_id)
    if parent_node is None or parent_node.deleted_at is not None:
        logger.warning(
            "Member %s apunta a group_id=%s sin Node espejo vivo; "
            "Node person queda huérfano.",
            member.id,
            member.group_id,
        )
        return None
    return parent_node.id


def _mirror_member_to_node_on_create(session: Session, member: Member) -> None:
    parent_node_id = _resolve_person_parent_node_id(session, member)
    node = Node(
        id=member.id,
        organization_id=member.organization_id,
        parent_node_id=parent_node_id,
        type=NodeType.PERSON,
        name=member.name,
        position_x=0.0,
        position_y=0.0,
        attrs=_build_person_attrs(member, prev_attrs=None),
        created_at=member.created_at,
    )
    session.add(node)


def _mirror_member_to_node_on_update(session: Session, member: Member) -> None:
    node = session.get(Node, member.id)
    if node is None:
        logger.error(
            "Member %s no tiene Node espejo durante PATCH (estado inconsistente). "
            "Creando Node on-the-fly.",
            member.id,
        )
        _mirror_member_to_node_on_create(session, member)
        return

    # Preservar claves custom (p. ej. admin_notes) seteadas vía PATCH /nodes.
    prev_attrs = dict(node.attrs) if isinstance(node.attrs, dict) else {}

    node.deleted_at = None
    node.name = member.name
    node.parent_node_id = _resolve_person_parent_node_id(session, member)
    node.attrs = _build_person_attrs(member, prev_attrs=prev_attrs)
    session.add(node)


def _mirror_member_to_node_on_delete(session: Session, member_id: UUID) -> None:
    node = session.get(Node, member_id)
    if node is None:
        logger.warning(
            "DELETE /members/%s: Node espejo no existe. No-op.", member_id
        )
        return
    if node.deleted_at is None:
        node.deleted_at = datetime.now(timezone.utc)
        session.add(node)


def _count_analyses_for_uuid(session: Session, target_id: UUID) -> int:
    """Cuenta análisis que referencian este UUID.

    Desde Sprint 3 la FK del motor se llama `node_id` (antes `group_id`).
    UUIDs globalmente únicos: el mismo UUID puede provenir de un Group
    legacy o de un Member legacy; ambos quedaron preservados en `nodes`
    durante la migración Sprint 1.2.
    """
    try:
        n = session.execute(
            text("SELECT COUNT(*) FROM node_analyses WHERE node_id = :uid"),
            {"uid": str(target_id)},
        ).scalar_one()
        g = session.execute(
            text("SELECT COUNT(*) FROM group_analyses WHERE node_id = :uid"),
            {"uid": str(target_id)},
        ).scalar_one()
    except Exception:
        return 0
    return int(n or 0) + int(g or 0)


# ─────────────────────────── Endpoints ──────────────────────────

@router.post(
    "/members",
    response_model=MemberRead,
    status_code=status.HTTP_201_CREATED,
    deprecated=True,
)
def create_member(
    payload: MemberCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> MemberRead:
    if not _can_access_org(current_user, payload.organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    _validate_group_assignment(session, payload.organization_id, payload.group_id)

    member = Member(
        organization_id=payload.organization_id,
        group_id=payload.group_id,
        name=payload.name,
        role_label=payload.role_label,
        interview_token=_generate_unique_token(session),
        token_status=MemberTokenStatus.PENDING,
    )
    session.add(member)
    session.flush()

    _mirror_member_to_node_on_create(session, member)

    session.commit()
    session.refresh(member)
    return MemberRead.model_validate(member)


@router.get("/members/{member_id}", response_model=MemberRead, deprecated=True)
def get_member(
    member_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> MemberRead:
    member = session.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    _ensure_member_access(member, current_user)
    return MemberRead.model_validate(member)


@router.patch("/members/{member_id}", response_model=MemberRead, deprecated=True)
def update_member(
    member_id: UUID,
    payload: MemberUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> MemberRead:
    member = session.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    _ensure_member_access(member, current_user)

    update_data = payload.model_dump(exclude_unset=True)
    if "group_id" in update_data:
        _validate_group_assignment(session, member.organization_id, update_data["group_id"])

    for field, value in update_data.items():
        setattr(member, field, value)

    session.add(member)
    session.flush()

    _mirror_member_to_node_on_update(session, member)

    session.commit()
    session.refresh(member)
    return MemberRead.model_validate(member)


@router.delete(
    "/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    deprecated=True,
)
def delete_member(
    member_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
):
    member = session.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    _ensure_member_access(member, current_user)

    # Protección Sprint 1.4: no permitir borrar si hay análisis asociados.
    if _count_analyses_for_uuid(session, member.id) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "El miembro tiene análisis históricos asociados. Use archivado "
                "(soft-delete) en lugar de eliminación."
            ),
        )

    session.delete(member)
    _mirror_member_to_node_on_delete(session, member_id)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/organizations/{org_id}/members",
    response_model=list[MemberRead],
    deprecated=True,
)
def list_members_by_organization(
    org_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> list[MemberRead]:
    if not _can_access_org(current_user, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    members = session.exec(select(Member).where(Member.organization_id == org_id)).all()
    return [MemberRead.model_validate(member) for member in members]


@router.get(
    "/groups/{group_id}/members",
    response_model=list[MemberRead],
    deprecated=True,
)
def list_members_by_group(
    group_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> list[MemberRead]:
    group = session.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    if not _can_access_org(current_user, group.organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    members = session.exec(select(Member).where(Member.group_id == group_id)).all()
    return [MemberRead.model_validate(member) for member in members]


@router.patch(
    "/members/{member_id}/group",
    response_model=MemberRead,
    deprecated=True,
)
def move_member_group(
    member_id: UUID,
    payload: MemberMoveGroup,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> MemberRead:
    member = session.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    _ensure_member_access(member, current_user)
    _validate_group_assignment(session, member.organization_id, payload.group_id)

    member.group_id = payload.group_id
    session.add(member)
    session.flush()

    _mirror_member_to_node_on_update(session, member)

    session.commit()
    session.refresh(member)
    return MemberRead.model_validate(member)
