from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlmodel import Field, SQLModel


class QuickAssessment(SQLModel, table=True):
    __tablename__ = "quick_assessments"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, nullable=False),
    )
    org_name: str = Field(nullable=False, max_length=255)
    org_type: str = Field(default="empresa", nullable=False, max_length=50)
    size_range: str = Field(default="1-10", nullable=False, max_length=20)
    owner_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    leader_responses: dict = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    scores: dict | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    member_count: int = Field(default=0, sa_column=Column(Integer, nullable=False, server_default="0"))
    responses_count: int = Field(default=0, sa_column=Column(Integer, nullable=False, server_default="0"))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class QuickAssessmentMember(SQLModel, table=True):
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
    responses: dict | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    submitted_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


# ── Schemas ───────────────────────────────────────────

class QuickAssessmentCreate(SQLModel):
    org_name: str
    org_type: str = "empresa"
    size_range: str = "1-10"
    leader_responses: dict


class MemberInvite(SQLModel):
    name: str
    role: str = ""
    email: str


class InviteMembersRequest(SQLModel):
    members: list[MemberInvite]


class MemberRespondRequest(SQLModel):
    token: str
    responses: dict[str, int]


class QuickAssessmentRead(SQLModel):
    id: UUID
    org_name: str
    org_type: str
    size_range: str
    leader_responses: dict
    scores: dict | None
    member_count: int
    responses_count: int
    created_at: datetime


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
