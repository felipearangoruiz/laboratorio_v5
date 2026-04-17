from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel


class Group(SQLModel, table=True):
    __tablename__ = "groups"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, nullable=False),
    )
    organization_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    parent_group_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("groups.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    node_type: str = Field(
        default="area",
        sa_column=Column(String(20), nullable=False, server_default="area"),
    )
    name: str = Field(nullable=False, max_length=255)
    description: str = Field(default="", nullable=False)
    tarea_general: str = Field(default="", nullable=False)
    email: str = Field(default="", sa_column=Column(String(255), nullable=False, server_default=""))
    area: str = Field(default="", sa_column=Column(String(255), nullable=False, server_default=""))
    nivel_jerarquico: int | None = Field(default=None)
    tipo_nivel: str | None = Field(default=None, max_length=255)
    position_x: float = Field(default=0.0, sa_column=Column(Float, nullable=False, server_default="0"))
    position_y: float = Field(default=0.0, sa_column=Column(Float, nullable=False, server_default="0"))
    is_default: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class GroupRead(SQLModel):
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
    is_default: bool
    created_at: datetime
