from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel


class MemberTokenStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EXPIRED = "expired"


class Member(SQLModel, table=True):
    __tablename__ = "members"

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
    group_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("groups.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    name: str = Field(nullable=False, max_length=255)
    role_label: str = Field(default="", nullable=False, max_length=255)
    interview_token: str = Field(
        default_factory=lambda: uuid4().hex,
        nullable=False,
        unique=True,
        index=True,
        max_length=32,
    )
    token_status: MemberTokenStatus = Field(
        default=MemberTokenStatus.PENDING,
        sa_column=Column(
            SAEnum(MemberTokenStatus, name="member_token_status", native_enum=True, create_type=False),
            nullable=False,
            server_default=MemberTokenStatus.PENDING.value,
        ),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class MemberRead(SQLModel):
    id: UUID
    organization_id: UUID
    group_id: UUID | None
    name: str
    role_label: str
    interview_token: str
    token_status: MemberTokenStatus
    created_at: datetime
