from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSON, UUID as PGUUID
from sqlmodel import Field, SQLModel


class QuickAssessmentStatus(str, Enum):
    WAITING = "waiting"
    READY = "ready"
    COMPLETED = "completed"


class QuickAssessment(SQLModel, table=True):
    __tablename__ = "quick_assessments"

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
    leader_responses: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, server_default="{}"),
    )
    scores: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, server_default="{}"),
    )
    member_count: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default="0"),
    )
    status: QuickAssessmentStatus = Field(
        default=QuickAssessmentStatus.WAITING,
        sa_column=Column(
            SAEnum(
                QuickAssessmentStatus,
                name="quick_assessment_status",
                native_enum=True,
                create_type=False,
                values_callable=lambda enum_cls: [m.value for m in enum_cls],
            ),
            nullable=False,
            server_default=QuickAssessmentStatus.WAITING.value,
        ),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class QuickAssessmentCreate(SQLModel):
    organization_id: UUID
    leader_responses: dict = {}


class QuickAssessmentRead(SQLModel):
    id: UUID
    organization_id: UUID
    leader_responses: dict
    scores: dict
    member_count: int
    status: QuickAssessmentStatus
    created_at: datetime


class QuickAssessmentMember(SQLModel, table=True):
    """Miembros invitados al diagnóstico rápido (plan free). No toca la tabla members existente."""

    __tablename__ = "quick_assessment_members"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, nullable=False),
    )
    assessment_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("quick_assessments.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    name: str = Field(nullable=False, max_length=255)
    role_label: str = Field(default="", nullable=False, max_length=255)
    email: str = Field(nullable=False, max_length=255)
    token: str = Field(
        default_factory=lambda: uuid4().hex,
        nullable=False,
        unique=True,
        index=True,
        max_length=32,
    )
    responses: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, server_default="{}"),
    )
    completed: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class QuickAssessmentMemberCreate(SQLModel):
    name: str
    role_label: str = ""
    email: str


class QuickAssessmentMemberRead(SQLModel):
    id: UUID
    assessment_id: UUID
    name: str
    role_label: str
    email: str
    token: str
    completed: bool
    created_at: datetime
