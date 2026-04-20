"""DiagnosisResult — stores complete diagnosis produced by the external Codex processor.

Status lifecycle:  processing → ready | failed
The backend never runs the analysis itself; it only receives, stores, and serves.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlmodel import Field, SQLModel


class DiagnosisResult(SQLModel, table=True):
    __tablename__ = "diagnosis_results"

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

    # 'processing' while Codex runs  →  'ready' on success  →  'failed' on error
    status: str = Field(
        default="processing",
        sa_column=Column(String(20), nullable=False, server_default="processing"),
    )

    # { dimension: { score, avg, std, node_scores: {node_id: score} } }
    scores: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="{}"),
    )

    # [{ id, title, description, dimension, confidence, node_ids[], type }]
    findings: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )

    # [{ id, priority, title, description, node_ids[] }]
    recommendations: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )

    # Full narrative in Markdown — rendered in DiagnosisPanel
    narrative_md: str = Field(
        default="",
        sa_column=Column(Text, nullable=False, server_default=""),
    )

    # Org graph snapshot at the moment of diagnosis (for historical comparison)
    structure_snapshot: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="{}"),
    )

    error: str | None = Field(
        default=None,
        sa_column=Column(String, nullable=True),
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    completed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )


class DiagnosisResultRead(SQLModel):
    id: UUID
    organization_id: UUID
    status: str
    scores: dict[str, Any]
    findings: list[Any]
    recommendations: list[Any]
    narrative_md: str
    structure_snapshot: dict[str, Any]
    error: str | None
    created_at: datetime
    completed_at: datetime | None


class DiagnosisCreate(SQLModel):
    """Request body for POST /organizations/{org_id}/diagnosis.

    Sent by the external Codex processor once analysis is complete.
    """
    scores: dict[str, Any]
    findings: list[Any]
    recommendations: list[Any]
    narrative_md: str
    structure_snapshot: dict[str, Any]
