from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey
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
    name: str = Field(nullable=False, max_length=255)
    description: str = Field(default="", nullable=False)
    tarea_general: str = Field(default="", nullable=False)
    nivel_jerarquico: int | None = Field(default=None)
    tipo_nivel: str | None = Field(default=None, max_length=255)
    is_default: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class GroupRead(SQLModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str
    tarea_general: str
    nivel_jerarquico: int | None
    tipo_nivel: str | None
    is_default: bool
    created_at: datetime
