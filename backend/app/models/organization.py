from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel


class Organization(SQLModel, table=True):
    __tablename__ = "organizations"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, nullable=False),
    )
    name: str = Field(nullable=False, max_length=255)
    description: str = Field(default="", nullable=False)
    sector: str = Field(default="", nullable=False, max_length=255)
    strategic_objectives: str = Field(default="", nullable=False)
    strategic_concerns: str = Field(default="", nullable=False)
    key_questions: str = Field(default="", nullable=False)
    additional_context: str = Field(default="", nullable=False)
    admin_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("users.id"),
            nullable=True,
        ),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class OrganizationCreate(SQLModel):
    name: str
    description: str = ""
    sector: str = ""
    strategic_objectives: str = ""
    strategic_concerns: str = ""
    key_questions: str = ""
    additional_context: str = ""
    admin_id: UUID | None = None


class OrganizationUpdate(SQLModel):
    name: str | None = None
    description: str | None = None
    sector: str | None = None
    strategic_objectives: str | None = None
    strategic_concerns: str | None = None
    key_questions: str | None = None
    additional_context: str | None = None
    admin_id: UUID | None = None


class OrganizationRead(SQLModel):
    id: UUID
    name: str
    description: str
    sector: str
    strategic_objectives: str
    strategic_concerns: str
    key_questions: str
    additional_context: str
    admin_id: UUID | None
    created_at: datetime
