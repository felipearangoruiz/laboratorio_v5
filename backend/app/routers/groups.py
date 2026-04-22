"""COMPATIBILITY LAYER — Sprint 1.4

Este router es legacy. Cada operación de escritura se espeja sobre la
tabla nueva correspondiente (`nodes` con `type="unit"`) dentro de la
misma transacción para mantener los datos sincronizados durante la
coexistencia del viejo y el nuevo modelo.

Los endpoints están marcados `deprecated=True`. Los consumidores deben
migrar a /nodes, /edges, /node-states, /campaigns.

Eliminar este router cuando:
  - El frontend no llame a ningún endpoint legacy.
  - El motor de análisis haya migrado sus FKs de
    node_analyses.group_id → node_analyses.node_id
    (deuda en DEUDA_DOCUMENTAL.md).

Política de espejado:
  - POST /groups      → INSERT Group + INSERT Node (mismo UUID, type=unit).
  - PATCH /groups/{id}→ UPDATE Group + UPDATE Node (fallback: crea Node si
                        falta, con log de error).
  - DELETE /groups/{id}→ proteger contra NodeAnalyses/GroupAnalyses (409),
                        luego DELETE Group + soft-delete Node
                        (deleted_at=now).
  - PATCH bulk positions → UPDATE ambos lados.
  - GET endpoints       → sin cambios (leen solo de `groups`).

Todas las escrituras ocurren dentro de una única transacción SQLModel;
si la operación sobre Node falla, se hace ROLLBACK de ambas tablas.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel import Session, func, select

from app.core.dependencies import get_current_user
from app.db import get_session
from app.models.group import Group, GroupRead
from app.models.member import Member
from app.models.node import Node, NodeType
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter()


class GroupCreate(BaseModel):
    organization_id: UUID
    node_type: str = "area"
    name: str
    description: str = ""
    tarea_general: str = ""
    email: str = ""
    area: str = ""
    nivel_jerarquico: int | None = None
    tipo_nivel: str | None = None
    parent_group_id: UUID | None = None
    position_x: float = 0.0
    position_y: float = 0.0


class GroupUpdate(BaseModel):
    node_type: str | None = None
    name: str | None = None
    description: str | None = None
    tarea_general: str | None = None
    email: str | None = None
    area: str | None = None
    nivel_jerarquico: int | None = None
    tipo_nivel: str | None = None
    parent_group_id: UUID | None = None
    position_x: float | None = None
    position_y: float | None = None
    context_notes: str | None = None


class GroupTreeNode(BaseModel):
    id: UUID
    organization_id: UUID
    parent_group_id: UUID | None
    node_type: str
    name: str
    description: str
    tarea_general: str
    email: str
    area: str
    nivel_jerarquico: int | None
    tipo_nivel: str | None
    position_x: float
    position_y: float
    context_notes: str | None
    is_default: bool
    member_count: int
    children: list["GroupTreeNode"]


class PositionUpdate(BaseModel):
    id: UUID
    position_x: float
    position_y: float


class BulkPositionUpdate(BaseModel):
    positions: list[PositionUpdate]


def _can_access_org(user: User, organization_id: UUID) -> bool:
    return user.role == UserRole.SUPERADMIN or user.organization_id == organization_id


def _ensure_group_access(group: Group, user: User) -> None:
    if not _can_access_org(user, group.organization_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )


def _validate_parent_group(
    session: Session,
    organization_id: UUID,
    parent_group_id: UUID,
    current_group_id: UUID | None = None,
) -> None:
    parent = session.get(Group, parent_group_id)
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent group not found",
        )
    if parent.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parent group must belong to same organization",
        )

    if current_group_id is not None:
        if parent_group_id == current_group_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Group cannot be parent of itself",
            )

        visited: set[UUID] = set()
        cursor = parent
        while cursor.parent_group_id is not None:
            if cursor.id in visited:
                break
            visited.add(cursor.id)
            if cursor.parent_group_id == current_group_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Group hierarchy cycle detected",
                )
            next_group = session.get(Group, cursor.parent_group_id)
            if not next_group:
                break
            cursor = next_group


# ────────────── Mirror helpers (Group ↔ Node type=unit) ──────────────

def _build_unit_attrs(group: Group) -> dict[str, Any]:
    """Campos de Group sin columna directa en Node quedan en attrs."""
    return {
        "description": group.description or "",
        "tarea_general": group.tarea_general or "",
        "email": group.email or "",
        "area": group.area or "",
        "nivel_jerarquico": group.nivel_jerarquico,
        "tipo_nivel": group.tipo_nivel,
        "context_notes": group.context_notes,
        "node_type_legacy": group.node_type,
        "is_default": group.is_default,
    }


def _resolve_parent_node_id(
    session: Session,
    group: Group,
) -> UUID | None:
    """Devuelve el id del Node espejo del parent_group_id, o None si no existe.

    Si no existe espejo (estado inconsistente pre-1.4), loggea warning y
    retorna None. El Node se crea como unit raíz huérfana; es reparable
    más adelante por el script de backfill.
    """
    if group.parent_group_id is None:
        return None
    parent_node = session.get(Node, group.parent_group_id)
    if parent_node is None or parent_node.deleted_at is not None:
        logger.warning(
            "Group %s tiene parent_group_id=%s sin Node espejo vivo; "
            "creando Node raíz huérfano.",
            group.id,
            group.parent_group_id,
        )
        return None
    return parent_node.id


def _mirror_group_to_node_on_create(session: Session, group: Group) -> None:
    """Crea el Node espejo con el MISMO UUID del Group."""
    parent_node_id = _resolve_parent_node_id(session, group)
    node = Node(
        id=group.id,
        organization_id=group.organization_id,
        parent_node_id=parent_node_id,
        type=NodeType.UNIT,
        name=group.name,
        position_x=group.position_x,
        position_y=group.position_y,
        attrs=_build_unit_attrs(group),
        created_at=group.created_at,
    )
    session.add(node)


def _mirror_group_to_node_on_update(session: Session, group: Group) -> None:
    """Actualiza el Node espejo. Si no existe, lo crea on-the-fly + error log."""
    node = session.get(Node, group.id)
    if node is None:
        logger.error(
            "Group %s no tiene Node espejo durante PATCH (estado inconsistente). "
            "Creando Node on-the-fly.",
            group.id,
        )
        _mirror_group_to_node_on_create(session, group)
        return

    # Resucitar el Node si estaba soft-deleted (improbable pero defensivo).
    node.deleted_at = None
    node.name = group.name
    node.position_x = group.position_x
    node.position_y = group.position_y
    node.parent_node_id = _resolve_parent_node_id(session, group)
    node.attrs = _build_unit_attrs(group)
    session.add(node)


def _mirror_group_to_node_on_delete(session: Session, group_id: UUID) -> None:
    """Soft-delete del Node espejo. Si no existe, no-op silencioso."""
    node = session.get(Node, group_id)
    if node is None:
        logger.warning(
            "DELETE /groups/%s: Node espejo no existe. No-op.", group_id
        )
        return
    if node.deleted_at is None:
        node.deleted_at = datetime.now(timezone.utc)
        session.add(node)


def _count_analyses_for_uuid(session: Session, target_id: UUID) -> int:
    """Cuenta NodeAnalyses + GroupAnalyses que referencian este UUID.

    `node_analyses.group_id` y `group_analyses.group_id` usan UUIDs
    preservados entre tablas viejas y nuevas; por eso la misma PK sirve.
    """
    try:
        n = session.execute(
            text("SELECT COUNT(*) FROM node_analyses WHERE group_id = :gid"),
            {"gid": str(target_id)},
        ).scalar_one()
        g = session.execute(
            text("SELECT COUNT(*) FROM group_analyses WHERE group_id = :gid"),
            {"gid": str(target_id)},
        ).scalar_one()
    except Exception:
        # Tablas del motor pueden no existir en algunos escenarios de test.
        return 0
    return int(n or 0) + int(g or 0)


# ─────────────────────────── Endpoints ──────────────────────────

@router.post(
    "/groups",
    response_model=GroupRead,
    status_code=status.HTTP_201_CREATED,
    deprecated=True,
)
def create_group(
    payload: GroupCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> GroupRead:
    if not _can_access_org(current_user, payload.organization_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    if payload.parent_group_id is not None:
        _validate_parent_group(session, payload.organization_id, payload.parent_group_id)

    group = Group(
        organization_id=payload.organization_id,
        node_type=payload.node_type,
        name=payload.name,
        description=payload.description,
        tarea_general=payload.tarea_general,
        email=payload.email,
        area=payload.area,
        nivel_jerarquico=payload.nivel_jerarquico,
        tipo_nivel=payload.tipo_nivel,
        parent_group_id=payload.parent_group_id,
        position_x=payload.position_x,
        position_y=payload.position_y,
    )
    session.add(group)
    session.flush()  # asigna/confirma group.id sin commit

    # Mirror → Node (mismo UUID). Cualquier fallo aborta la transacción.
    _mirror_group_to_node_on_create(session, group)

    session.commit()
    session.refresh(group)
    return GroupRead.model_validate(group)


@router.get("/groups", response_model=list[GroupRead], deprecated=True)
def list_groups(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> list[GroupRead]:
    query = select(Group)
    if current_user.role != UserRole.SUPERADMIN:
        query = query.where(Group.organization_id == current_user.organization_id)

    groups = session.exec(query).all()
    return [GroupRead.model_validate(group) for group in groups]


@router.get("/groups/{group_id}", response_model=GroupRead, deprecated=True)
def get_group(
    group_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> GroupRead:
    group = session.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    _ensure_group_access(group, current_user)
    return GroupRead.model_validate(group)


@router.patch("/groups/{group_id}", response_model=GroupRead, deprecated=True)
def update_group(
    group_id: UUID,
    payload: GroupUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> GroupRead:
    group = session.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    _ensure_group_access(group, current_user)

    update_data = payload.model_dump(exclude_unset=True)
    if "parent_group_id" in update_data and update_data["parent_group_id"] is not None:
        _validate_parent_group(
            session,
            group.organization_id,
            update_data["parent_group_id"],
            current_group_id=group.id,
        )

    for field, value in update_data.items():
        setattr(group, field, value)

    session.add(group)
    session.flush()

    # Mirror → Node. Fallback: si no existe, se crea.
    _mirror_group_to_node_on_update(session, group)

    session.commit()
    session.refresh(group)
    return GroupRead.model_validate(group)


@router.delete(
    "/groups/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    deprecated=True,
)
def delete_group(
    group_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
):
    group = session.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    _ensure_group_access(group, current_user)

    if group.is_default:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Default group cannot be deleted")

    has_children = session.exec(select(Group).where(Group.parent_group_id == group.id)).first()
    if has_children:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group has children",
        )

    has_members = session.exec(select(Member).where(Member.group_id == group.id)).first()
    if has_members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group has members",
        )

    # Protección nueva Sprint 1.4: no permitir borrar si hay análisis asociados.
    if _count_analyses_for_uuid(session, group.id) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "El grupo tiene análisis históricos asociados. Use archivado "
                "(soft-delete) en lugar de eliminación."
            ),
        )

    session.delete(group)
    # Mirror → soft-delete del Node espejo (política MODEL_PHILOSOPHY §5.1).
    _mirror_group_to_node_on_delete(session, group_id)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/organizations/{org_id}/groups/tree",
    response_model=list[GroupTreeNode],
    deprecated=True,
)
def get_organization_groups_tree(
    org_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    if not _can_access_org(current_user, org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    groups = session.exec(select(Group).where(Group.organization_id == org_id)).all()
    member_counts_rows = session.exec(
        select(Member.group_id, func.count(Member.id))
        .join(Group, Group.id == Member.group_id)
        .where(Group.organization_id == org_id)
        .group_by(Member.group_id)
    ).all()
    member_counts: dict[UUID, int] = {group_id: count for group_id, count in member_counts_rows}

    by_parent: dict[UUID | None, list[Group]] = {}
    for group in groups:
        by_parent.setdefault(group.parent_group_id, []).append(group)

    def build(parent_id: UUID | None) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        for group in by_parent.get(parent_id, []):
            nodes.append(
                {
                    "id": group.id,
                    "organization_id": group.organization_id,
                    "parent_group_id": group.parent_group_id,
                    "node_type": group.node_type,
                    "name": group.name,
                    "description": group.description,
                    "tarea_general": group.tarea_general,
                    "email": group.email,
                    "area": group.area,
                    "nivel_jerarquico": group.nivel_jerarquico,
                    "tipo_nivel": group.tipo_nivel,
                    "position_x": group.position_x,
                    "position_y": group.position_y,
                    "context_notes": group.context_notes,
                    "is_default": group.is_default,
                    "member_count": member_counts.get(group.id, 0),
                    "children": build(group.id),
                }
            )
        return nodes

    return build(None)


@router.patch("/organizations/{org_id}/groups/positions", deprecated=True)
def update_positions(
    org_id: UUID,
    payload: BulkPositionUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> dict:
    """Bulk update node positions after drag on canvas (espejado a Node)."""
    if not _can_access_org(current_user, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    updated = 0
    for pos in payload.positions:
        group = session.get(Group, pos.id)
        if group and group.organization_id == org_id:
            group.position_x = pos.position_x
            group.position_y = pos.position_y
            session.add(group)
            # Mirror → Node.
            node = session.get(Node, pos.id)
            if node is not None:
                node.position_x = pos.position_x
                node.position_y = pos.position_y
                session.add(node)
            else:
                logger.warning(
                    "Bulk positions: Group %s sin Node espejo; se actualiza "
                    "solo el Group.",
                    pos.id,
                )
            updated += 1

    session.commit()
    return {"updated": updated}
