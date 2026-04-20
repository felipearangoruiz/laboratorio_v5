from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlmodel import Field, SQLModel


class Interview(SQLModel, table=True):
    __tablename__ = "interviews"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, nullable=False),
    )
    member_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("members.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        )
    )
    organization_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("organizations.id"),
            nullable=False,
        )
    )
    group_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("groups.id"),
            nullable=True,
        ),
    )
    data: dict[str, Any] = Field(
        sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    )
    submitted_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    schema_version: int = Field(default=1, nullable=False)


class InterviewRead(SQLModel):
    id: UUID
    member_id: UUID
    organization_id: UUID
    group_id: UUID | None
    data: dict[str, Any]
    submitted_at: datetime | None
    schema_version: int
