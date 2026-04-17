from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID as PGUUID
from sqlmodel import Field, SQLModel


class QuickAssessmentStatus(str, Enum):
    WAITING = "waiting"
    READY = "ready"
    COMPLETED = "completed"


# ── Table: quick_assessments ────────────────────────────────────────────────

class QuickAssessment(SQLModel, table=True):
    """Assessment del flujo Free (sin auth).

    owner_id es nullable para permitir assessments anónimos que luego pueden
    vincularse a una cuenta cuando el usuario haga /register desde la score page.
    """

    __tablename__ = "quick_assessments"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, nullable=False),
    )
    owner_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    org_name: str = Field(nullable=False, max_length=255)
    org_type: str = Field(default="", nullable=False, max_length=50)
    size_range: str = Field(default="", nullable=False, max_length=50)
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
    responses_count: int = Field(
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


# ── Table: quick_assessment_members ─────────────────────────────────────────

class QuickAssessmentMember(SQLModel, table=True):
    """Miembros invitados al diagnóstico rápido (plan free)."""

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
    role: str = Field(default="", nullable=False, max_length=255)
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
    submitted_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


# ── Pydantic request / response schemas ─────────────────────────────────────

class QuickAssessmentCreate(SQLModel):
    """POST / body — crear un assessment anónimo (sin owner)."""

    org_name: str
    org_type: str = ""
    size_range: str = ""
    leader_responses: dict = {}


class QuickAssessmentRead(SQLModel):
    id: UUID
    owner_id: UUID | None
    org_name: str
    org_type: str
    size_range: str
    leader_responses: dict
    scores: dict
    member_count: int
    responses_count: int
    status: QuickAssessmentStatus
    created_at: datetime


class InviteMember(SQLModel):
    """Un miembro a invitar (item de InviteMembersRequest)."""

    name: str
    role: str = ""
    email: str


class InviteMembersRequest(SQLModel):
    """POST /{assessment_id}/invite body."""

    members: list[InviteMember]


class MemberRespondRequest(SQLModel):
    """POST /interview/{token}/submit y /{assessment_id}/respond body."""

    token: str | None = None
    responses: dict


class DimensionScoreRead(SQLModel):
    dimension: str
    label: str
    score: float
    max_score: float


class QuickAssessmentScoreRead(SQLModel):
    id: UUID
    org_name: str
    dimensions: list[DimensionScoreRead]
    member_count: int
    responses_count: int
    created_at: datetime


class QuickAssessmentMemberCreate(SQLModel):
    name: str
    role: str = ""
    email: str


class QuickAssessmentMemberRead(SQLModel):
    id: UUID
    assessment_id: UUID
    name: str
    role: str
    email: str
    token: str
    submitted_at: datetime | None
    created_at: datetime
