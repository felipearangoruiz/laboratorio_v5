from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlmodel import Field, SQLModel


class NodeStateStatus(str, Enum):
    INVITED = "invited"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class NodeState(SQLModel, table=True):
    __tablename__ = "node_states"
    __table_args__ = (UniqueConstraint("node_id", "campaign_id", name="uq_node_state_node_campaign"),)

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, nullable=False),
    )
    node_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("nodes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    campaign_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("assessment_campaigns.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    email_assigned: str | None = Field(
        default=None,
        sa_column=Column(String(255), nullable=True),
    )
    role_label: str | None = Field(
        default=None,
        sa_column=Column(String(255), nullable=True),
    )
    context_notes: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )
    respondent_token: str | None = Field(
        default=None,
        sa_column=Column(String(64), nullable=True, unique=True, index=True),
    )
    status: NodeStateStatus = Field(
        default=NodeStateStatus.INVITED,
        sa_column=Column(
            SAEnum(
                NodeStateStatus,
                name="node_state_status_enum",
                native_enum=True,
                create_type=False,
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
            server_default=NodeStateStatus.INVITED.value,
        ),
    )
    # Datos de respuesta del respondiente. NULL mientras status=invited o skipped;
    # parcial mientras status=in_progress; completo cuando status=completed.
    # Preserva el JSON exacto de interviews.data para trazabilidad histórica.
    interview_data: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    invited_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    completed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class NodeStateRead(SQLModel):
    id: UUID
    node_id: UUID
    campaign_id: UUID
    email_assigned: str | None
    role_label: str | None
    context_notes: str | None
    respondent_token: str | None
    status: NodeStateStatus
    interview_data: dict[str, Any] | None
    invited_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
