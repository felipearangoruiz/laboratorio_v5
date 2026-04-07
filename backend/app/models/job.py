from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel


class JobState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatus(SQLModel, table=True):
    __tablename__ = "job_statuses"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, nullable=False),
    )
    organization_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("organizations.id"),
            nullable=False,
        )
    )
    status: JobState = Field(
        default=JobState.PENDING,
        sa_column=Column(
            SAEnum(JobState, name="job_state", native_enum=True, create_type=False),
            nullable=False,
            server_default=JobState.PENDING.value,
        ),
    )
    error: str | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class JobStatusRead(SQLModel):
    id: UUID
    organization_id: UUID
    status: JobState
    error: str | None
    created_at: datetime
    updated_at: datetime
