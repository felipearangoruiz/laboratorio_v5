from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel


class LateralRelation(SQLModel, table=True):
    __tablename__ = "lateral_relations"

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
    source_node_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("groups.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    target_node_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("groups.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    type: str = Field(
        default="colaboracion",
        sa_column=Column(String(50), nullable=False, server_default="colaboracion"),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class LateralRelationRead(SQLModel):
    id: UUID
    organization_id: UUID
    source_node_id: UUID
    target_node_id: UUID
    type: str
    created_at: datetime


class LateralRelationCreate(SQLModel):
    source_node_id: UUID
    target_node_id: UUID
    type: str = "colaboracion"
