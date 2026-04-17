from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlmodel import Session, func, select

from app.core.dependencies import get_current_user
from app.db import get_session
from app.models.group import Group, GroupRead
from app.models.member import Member
from app.models.user import User, UserRole

router = APIRouter()


class GroupCreate(BaseModel):
    organization_id: UUID
    name: str
    description: str = ""
    tarea_general: str = ""
    area: str = ""
    nivel_jerarquico: int | None = None
    tipo_nivel: str | None = None
    parent_group_id: UUID | None = None
    position_x: float = 0.0
    position_y: float = 0.0


class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    tarea_general: str | None = None
    area: str | None = None
    nivel_jerarquico: int | None = None
    tipo_nivel: str | None = None
    parent_group_id: UUID | None = None
    position_x: float | None = None
    position_y: float | None = None


class GroupTreeNode(BaseModel):
    id: UUID
    organization_id: UUID
    parent_group_id: UUID | None
    name: str
    description: str
    tarea_general: str
    area: str
    nivel_jerarquico: int | None
    tipo_nivel: str | None
    position_x: float
    position_y: float
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


@router.post("/groups", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
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
        name=payload.name,
        description=payload.description,
        tarea_general=payload.tarea_general,
        area=payload.area,
        nivel_jerarquico=payload.nivel_jerarquico,
        tipo_nivel=payload.tipo_nivel,
        parent_group_id=payload.parent_group_id,
        position_x=payload.position_x,
        position_y=payload.position_y,
    )
    session.add(group)
    session.commit()
    session.refresh(group)
    return GroupRead.model_validate(group)


@router.get("/groups", response_model=list[GroupRead])
def list_groups(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> list[GroupRead]:
    query = select(Group)
    if current_user.role != UserRole.SUPERADMIN:
        query = query.where(Group.organization_id == current_user.organization_id)

    groups = session.exec(query).all()
    return [GroupRead.model_validate(group) for group in groups]


@router.get("/groups/{group_id}", response_model=GroupRead)
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


@router.patch("/groups/{group_id}", response_model=GroupRead)
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
    session.commit()
    session.refresh(group)
    return GroupRead.model_validate(group)


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
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

    session.delete(group)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/organizations/{org_id}/groups/tree", response_model=list[GroupTreeNode])
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
                    "name": group.name,
                    "description": group.description,
                    "tarea_general": group.tarea_general,
                    "area": group.area,
                    "nivel_jerarquico": group.nivel_jerarquico,
                    "tipo_nivel": group.tipo_nivel,
                    "position_x": group.position_x,
                    "position_y": group.position_y,
                    "is_default": group.is_default,
                    "member_count": member_counts.get(group.id, 0),
                    "children": build(group.id),
                }
            )
        return nodes

    return build(None)


@router.patch("/organizations/{org_id}/groups/positions")
def update_positions(
    org_id: UUID,
    payload: BulkPositionUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> dict:
    """Bulk update node positions after drag on canvas."""
    if not _can_access_org(current_user, org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    updated = 0
    for pos in payload.positions:
        group = session.get(Group, pos.id)
        if group and group.organization_id == org_id:
            group.position_x = pos.position_x
            group.position_y = pos.position_y
            session.add(group)
            updated += 1

    session.commit()
    return {"updated": updated}
