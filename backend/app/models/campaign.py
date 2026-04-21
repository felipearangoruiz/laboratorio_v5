from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"


class AssessmentCampaign(SQLModel, table=True):
    __tablename__ = "assessment_campaigns"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, nullable=False),
    )
    organization_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    created_by_user_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    name: str = Field(sa_column=Column(String(255), nullable=False))
    status: CampaignStatus = Field(
        default=CampaignStatus.DRAFT,
        sa_column=Column(
            SAEnum(
                CampaignStatus,
                name="campaign_status_enum",
                native_enum=True,
                create_type=False,
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
            server_default=CampaignStatus.DRAFT.value,
        ),
    )
    started_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    closed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class AssessmentCampaignRead(SQLModel):
    id: UUID
    organization_id: UUID
    created_by_user_id: UUID | None
    name: str
    status: CampaignStatus
    started_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
