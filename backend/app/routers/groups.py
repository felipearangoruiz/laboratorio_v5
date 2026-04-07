from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Field, SQLModel, Session, select

from app.core.dependencies import get_current_user
from app.db import get_session
from app.models.group import Group, GroupRead
from app.models.member import Member
from app.models.organization import Organization
from app.models.user import User, UserRole

router = APIRouter(tags=["groups"])


class GroupCreate(SQLModel):
    organization_id: UUID
    parent_group_id: UUID | None = None
    name: str
    description: str = ""
    tarea_general: str = ""
    nivel_jerarquico: int | None = None
    tipo_nivel: str | None = None
    is_default: bool = False


class GroupUpdate(SQLModel):
    parent_group_id: UUID | None = None
    name: str | None = None
    description: str | None = None
    tarea_general: str | None = None
    nivel_jerarquico: int | None = None
    tipo_nivel: str | None = None
    is_default: bool | None = None


class GroupTreeNode(SQLModel):
    id: UUID
    organization_id: UUID
    parent_group_id: UUID | None
    name: str
    description: str
    tarea_general: str
    nivel_jerarquico: int | None
    tipo_nivel: str | None
    is_default: bool
    created_at: datetime
    children: list["GroupTreeNode"] = Field(default_factory=list)


GroupTreeNode.model_rebuild()


def _ensure_org_access(current_user: User, organization_id: UUID) -> None:
    if (
        current_user.role != UserRole.SUPERADMIN
        and current_user.organization_id != organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )


def _get_group_or_404(session: Session, group_id: UUID) -> Group:
    group = session.get(Group, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
    return group


def _validate_parent_group(
    session: Session,
    organization_id: UUID,
    parent_group_id: UUID | None,
    current_group_id: UUID | None = None,
) -> None:
    if parent_group_id is None:
        return

    parent_group = session.get(Group, parent_group_id)
    if not parent_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent group not found",
        )

    if parent_group.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parent group must belong to the same organization",
        )

    if current_group_id is None:
        return

    if parent_group_id == current_group_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group cannot be its own parent",
        )

    cursor = parent_group
    while cursor.parent_group_id is not None:
        if cursor.parent_group_id == current_group_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Group hierarchy cycle detected",
            )
        next_parent = session.get(Group, cursor.parent_group_id)
        if not next_parent:
            break
        cursor = next_parent


def _build_tree(groups: list[Group]) -> list[GroupTreeNode]:
    nodes_by_id: dict[UUID, GroupTreeNode] = {}
    roots: list[GroupTreeNode] = []

    for group in groups:
        nodes_by_id[group.id] = GroupTreeNode(
            id=group.id,
            organization_id=group.organization_id,
            parent_group_id=group.parent_group_id,
            name=group.name,
            description=group.description,
            tarea_general=group.tarea_general,
            nivel_jerarquico=group.nivel_jerarquico,
            tipo_nivel=group.tipo_nivel,
            is_default=group.is_default,
            created_at=group.created_at,
            children=[],
        )

    for group in groups:
        node = nodes_by_id[group.id]
        if group.parent_group_id is None:
            roots.append(node)
            continue

        parent = nodes_by_id.get(group.parent_group_id)
        if parent is None:
            roots.append(node)
            continue

        parent.children.append(node)

    return roots


@router.post("/groups", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> GroupRead:
    _ensure_org_access(current_user, payload.organization_id)

    organization = session.get(Organization, payload.organization_id)
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    _validate_parent_group(session, payload.organization_id, payload.parent_group_id)

    group = Group(**payload.model_dump())
    session.add(group)
    session.commit()
    session.refresh(group)
    return GroupRead.model_validate(group)


@router.get("/groups", response_model=list[GroupRead])
def list_groups(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> list[GroupRead]:
    statement = select(Group)
    if current_user.role != UserRole.SUPERADMIN:
        statement = statement.where(Group.organization_id == current_user.organization_id)

    groups = session.exec(statement).all()
    return [GroupRead.model_validate(group) for group in groups]


@router.get("/groups/{group_id}", response_model=GroupRead)
def get_group(
    group_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> GroupRead:
    group = _get_group_or_404(session, group_id)
    _ensure_org_access(current_user, group.organization_id)
    return GroupRead.model_validate(group)


@router.patch("/groups/{group_id}", response_model=GroupRead)
def update_group(
    group_id: UUID,
    payload: GroupUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> GroupRead:
    group = _get_group_or_404(session, group_id)
    _ensure_org_access(current_user, group.organization_id)

    update_data = payload.model_dump(exclude_unset=True)
    if "parent_group_id" in update_data:
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
) -> None:
    group = _get_group_or_404(session, group_id)
    _ensure_org_access(current_user, group.organization_id)

    if session.exec(select(Group.id).where(Group.parent_group_id == group_id)).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Group has child groups")

    if session.exec(select(Member.id).where(Member.group_id == group_id)).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Group has associated members")

    if group.is_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Default group cannot be deleted",
        )

    session.delete(group)
    session.commit()


@router.get("/organizations/{org_id}/groups/tree", response_model=list[GroupTreeNode])
def get_group_tree(
    org_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> list[GroupTreeNode]:
    _ensure_org_access(current_user, org_id)

    organization = session.get(Organization, org_id)
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    groups = session.exec(select(Group).where(Group.organization_id == org_id)).all()
    return _build_tree(groups)
