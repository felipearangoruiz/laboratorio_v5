from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.dependencies import get_current_user
from app.db import get_session
from app.models.group import Group, GroupRead
from app.models.user import User, UserRole

router = APIRouter()


class GroupCreate(BaseModel):
    name: str
    description: str = ""
    tarea_general: str = ""
    nivel_jerarquico: int | None = None
    tipo_nivel: str | None = None
    parent_group_id: UUID | None = None


class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    tarea_general: str | None = None
    nivel_jerarquico: int | None = None
    tipo_nivel: str | None = None
    parent_group_id: UUID | None = None


def _ensure_group_access(group: Group, user: User) -> None:
    if user.role != UserRole.SUPERADMIN and user.organization_id != group.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )


@router.post("/groups", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> GroupRead:
    if current_user.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user has no organization",
        )

    if payload.parent_group_id is not None:
        parent = session.get(Group, payload.parent_group_id)
        if not parent or parent.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid parent group",
            )

    group = Group(
        organization_id=current_user.organization_id,
        name=payload.name,
        description=payload.description,
        tarea_general=payload.tarea_general,
        nivel_jerarquico=payload.nivel_jerarquico,
        tipo_nivel=payload.tipo_nivel,
        parent_group_id=payload.parent_group_id,
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
        parent = session.get(Group, update_data["parent_group_id"])
        if not parent or parent.organization_id != group.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid parent group",
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
) -> None:
    group = session.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    _ensure_group_access(group, current_user)

    if group.is_default:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Default group cannot be deleted")

    has_children = session.exec(select(Group).where(Group.parent_group_id == group.id)).first()
    if has_children:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Group has children",
        )

    session.delete(group)
    session.commit()


@router.get("/organizations/{org_id}/groups/tree")
def get_organization_groups_tree(
    org_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    if current_user.role != UserRole.SUPERADMIN and current_user.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    groups = session.exec(select(Group).where(Group.organization_id == org_id)).all()
    by_parent: dict[UUID | None, list[Group]] = {}
    for group in groups:
        by_parent.setdefault(group.parent_group_id, []).append(group)

    def build(parent_id: UUID | None) -> list[dict[str, Any]]:
        return [
            {
                "id": str(group.id),
                "organization_id": str(group.organization_id),
                "parent_group_id": str(group.parent_group_id) if group.parent_group_id else None,
                "name": group.name,
                "description": group.description,
                "tarea_general": group.tarea_general,
                "nivel_jerarquico": group.nivel_jerarquico,
                "tipo_nivel": group.tipo_nivel,
                "is_default": group.is_default,
                "children": build(group.id),
            }
            for group in by_parent.get(parent_id, [])
        ]

    return build(None)
