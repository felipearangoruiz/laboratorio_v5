from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlmodel import Field, SQLModel


class ProcessingType(str, Enum):
    CIEGO = "CIEGO"
    ORIENTADO = "ORIENTADO"
    ORIENTACION = "ORIENTACION"


class ProcessingResult(SQLModel, table=True):
    __tablename__ = "processing_results"

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
    group_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("groups.id"),
            nullable=True,
        ),
    )
    type: ProcessingType = Field(
        sa_column=Column(
            SAEnum(ProcessingType, name="processing_type", native_enum=True, create_type=False),
            nullable=False,
        )
    )
    result: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class ProcessingResultRead(SQLModel):
    id: UUID
    organization_id: UUID
    group_id: UUID | None
    type: ProcessingType
    result: dict[str, Any]
    created_at: datetime
