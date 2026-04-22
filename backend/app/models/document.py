from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel

# campaign_id added in Sprint 1 (Prompt 1.1) — NULL = documento institucional
# permanente (participa en todas las campañas); NOT NULL = documento específico
# de esa campaña (ver MODEL_PHILOSOPHY.md §6.3).


class DocType(str, Enum):
    INSTITUTIONAL = "institutional"
    OTHER = "other"


class Document(SQLModel, table=True):
    __tablename__ = "documents"

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
    label: str = Field(sa_column=Column(String(255), nullable=False))
    doc_type: str = Field(
        default=DocType.INSTITUTIONAL.value,
        sa_column=Column(String(50), nullable=False, server_default=DocType.INSTITUTIONAL.value),
    )
    filename: str = Field(sa_column=Column(String(255), nullable=False))
    filepath: str = Field(sa_column=Column(String(512), nullable=False))
    campaign_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("assessment_campaigns.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    node_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("nodes.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class DocumentRead(SQLModel):
    id: UUID
    organization_id: UUID
    campaign_id: UUID | None
    node_id: UUID | None
    label: str
    doc_type: str
    filename: str
    created_at: datetime
