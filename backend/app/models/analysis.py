"""Motor de análisis — modelos SQLModel para el pipeline de 4 pasos.

Tablas (en orden FK):
  analysis_runs → node_analyses, group_analyses, org_analyses,
  document_extractions, findings → recommendations → evidence_links

Cada tabla tiene:
  - Clase Table (SQLModel, table=True)  — persiste en PostgreSQL
  - Clase Read  (SQLModel)              — response schema
  - Clase Create (SQLModel)             — request body schema (donde aplica)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlmodel import Field, SQLModel


# ─────────────────────────────────────────────────────────────────────────────
# 1. AnalysisRun
# ─────────────────────────────────────────────────────────────────────────────

class AnalysisRun(SQLModel, table=True):
    __tablename__ = "analysis_runs"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, nullable=False),
    )
    org_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    # pending | running | completed | failed
    status: str = Field(
        default="pending",
        sa_column=Column(String(20), nullable=False, server_default="pending"),
    )
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    completed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    model_used: str | None = Field(
        default=None,
        sa_column=Column(String(100), nullable=True),
    )
    total_nodes: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default="0"),
    )
    total_groups: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default="0"),
    )
    error_message: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )


class AnalysisRunRead(SQLModel):
    id: UUID
    org_id: UUID
    status: str
    started_at: datetime
    completed_at: datetime | None
    model_used: str | None
    total_nodes: int
    total_groups: int
    error_message: str | None


class AnalysisRunCreate(SQLModel):
    org_id: UUID
    model_used: str | None = None
    total_nodes: int = 0
    total_groups: int = 0


# ─────────────────────────────────────────────────────────────────────────────
# 2. NodeAnalysis  (Paso 1 — extracción por nodo)
# ─────────────────────────────────────────────────────────────────────────────

class NodeAnalysis(SQLModel, table=True):
    __tablename__ = "node_analyses"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, nullable=False),
    )
    run_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    org_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    group_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("groups.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    signals_positive: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    signals_tension: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    themes: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    dimensions_touched: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    # observacion | juicio | hipotesis
    evidence_type: str | None = Field(
        default=None,
        sa_column=Column(String(20), nullable=True),
    )
    # baja | media | alta
    emotional_intensity: str | None = Field(
        default=None,
        sa_column=Column(String(10), nullable=True),
    )
    key_quotes: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    context_notes_used: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default="false"),
    )
    confidence: float = Field(
        default=0.5,
        sa_column=Column(Float, nullable=False, server_default="0.5"),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class NodeAnalysisRead(SQLModel):
    id: UUID
    run_id: UUID
    org_id: UUID
    group_id: UUID
    signals_positive: list[Any]
    signals_tension: list[Any]
    themes: list[Any]
    dimensions_touched: list[Any]
    evidence_type: str | None
    emotional_intensity: str | None
    key_quotes: list[Any]
    context_notes_used: bool
    confidence: float
    created_at: datetime


class NodeAnalysisCreate(SQLModel):
    run_id: UUID
    org_id: UUID
    group_id: UUID
    signals_positive: list[str] = []
    signals_tension: list[str] = []
    themes: list[str] = []
    dimensions_touched: list[str] = []
    evidence_type: str | None = None
    emotional_intensity: str | None = None
    key_quotes: list[str] = []
    context_notes_used: bool = False
    confidence: float = 0.5


# ─────────────────────────────────────────────────────────────────────────────
# 3. GroupAnalysis  (Paso 2 — síntesis por grupo)
# ─────────────────────────────────────────────────────────────────────────────

class GroupAnalysis(SQLModel, table=True):
    __tablename__ = "group_analyses"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, nullable=False),
    )
    run_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    org_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    group_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("groups.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    # [{"pattern": str, "frequency": int}]
    patterns_internal: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    dominant_themes: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    # bajo | medio | alto | critico
    tension_level: str | None = Field(
        default=None,
        sa_column=Column(String(10), nullable=True),
    )
    # {dimension: score}
    scores_by_dimension: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="{}"),
    )
    gap_leader_team: float | None = Field(
        default=None,
        sa_column=Column(Float, nullable=True),
    )
    coverage: float = Field(
        default=0.0,
        sa_column=Column(Float, nullable=False, server_default="0.0"),
    )
    confidence: float = Field(
        default=0.5,
        sa_column=Column(Float, nullable=False, server_default="0.5"),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class GroupAnalysisRead(SQLModel):
    id: UUID
    run_id: UUID
    org_id: UUID
    group_id: UUID
    patterns_internal: list[Any]
    dominant_themes: list[Any]
    tension_level: str | None
    scores_by_dimension: dict[str, Any]
    gap_leader_team: float | None
    coverage: float
    confidence: float
    created_at: datetime


class GroupAnalysisCreate(SQLModel):
    run_id: UUID
    org_id: UUID
    group_id: UUID
    patterns_internal: list[Any] = []
    dominant_themes: list[str] = []
    tension_level: str | None = None
    scores_by_dimension: dict[str, float] = {}
    gap_leader_team: float | None = None
    coverage: float = 0.0
    confidence: float = 0.5


# ─────────────────────────────────────────────────────────────────────────────
# 4. OrgAnalysis  (Paso 3 — análisis organizacional)
# ─────────────────────────────────────────────────────────────────────────────

class OrgAnalysis(SQLModel, table=True):
    __tablename__ = "org_analyses"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, nullable=False),
    )
    run_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    org_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    # [{"pattern": str, "groups_affected": [id]}]
    cross_patterns: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    # [{"formal": str, "real": str, "evidence": str}]
    contradictions: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    # [{"risk": str, "nodes": [id], "severity": str}]
    structural_risks: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    # {dimension: {score, std, gap_leader_team}}
    dimension_scores: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="{}"),
    )
    # {centrality: {}, bridge_nodes: [], isolated_nodes: []}
    network_metrics: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="{}"),
    )
    confidence: float = Field(
        default=0.5,
        sa_column=Column(Float, nullable=False, server_default="0.5"),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class OrgAnalysisRead(SQLModel):
    id: UUID
    run_id: UUID
    org_id: UUID
    cross_patterns: list[Any]
    contradictions: list[Any]
    structural_risks: list[Any]
    dimension_scores: dict[str, Any]
    network_metrics: dict[str, Any]
    confidence: float
    created_at: datetime


class OrgAnalysisCreate(SQLModel):
    run_id: UUID
    org_id: UUID
    cross_patterns: list[Any] = []
    contradictions: list[Any] = []
    structural_risks: list[Any] = []
    dimension_scores: dict[str, Any] = {}
    network_metrics: dict[str, Any] = {}
    confidence: float = 0.5


# ─────────────────────────────────────────────────────────────────────────────
# 5. DocumentExtraction  (procesado en background al subir documentos)
# ─────────────────────────────────────────────────────────────────────────────

class DocumentExtraction(SQLModel, table=True):
    __tablename__ = "document_extractions"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, nullable=False),
    )
    run_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    org_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    doc_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    # financial | strategic | operational | hr | other
    doc_type: str = Field(
        sa_column=Column(String(20), nullable=False),
    )
    extracted_structure: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="{}"),
    )
    key_indicators: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="{}"),
    )
    implicit_signals: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    # 1, 2 or 3 — which pipeline step injects this extraction
    injected_at_step: int = Field(
        default=1,
        sa_column=Column(Integer, nullable=False, server_default="1"),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class DocumentExtractionRead(SQLModel):
    id: UUID
    run_id: UUID
    org_id: UUID
    doc_id: UUID
    doc_type: str
    extracted_structure: dict[str, Any]
    key_indicators: dict[str, Any]
    implicit_signals: list[Any]
    injected_at_step: int
    created_at: datetime


class DocumentExtractionCreate(SQLModel):
    run_id: UUID
    org_id: UUID
    doc_id: UUID
    doc_type: str
    extracted_structure: dict[str, Any] = {}
    key_indicators: dict[str, Any] = {}
    implicit_signals: list[Any] = []
    injected_at_step: int = 1


# ─────────────────────────────────────────────────────────────────────────────
# 6. Finding  (Paso 4 — hallazgos de síntesis ejecutiva)
# ─────────────────────────────────────────────────────────────────────────────

class Finding(SQLModel, table=True):
    __tablename__ = "findings"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, nullable=False),
    )
    run_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    org_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    title: str = Field(
        sa_column=Column(String(500), nullable=False),
    )
    description: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    # observacion | patron | inferencia | hipotesis
    type: str = Field(
        sa_column=Column(String(20), nullable=False),
    )
    # baja | media | alta | critica
    severity: str = Field(
        default="media",
        sa_column=Column(String(10), nullable=False, server_default="media"),
    )
    dimensions: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    # list of group UUIDs affected
    node_ids: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    confidence: float = Field(
        default=0.5,
        sa_column=Column(Float, nullable=False, server_default="0.5"),
    )
    confidence_rationale: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class FindingRead(SQLModel):
    id: UUID
    run_id: UUID
    org_id: UUID
    title: str
    description: str
    type: str
    severity: str
    dimensions: list[Any]
    node_ids: list[Any]
    confidence: float
    confidence_rationale: str | None
    created_at: datetime


class FindingCreate(SQLModel):
    run_id: UUID
    org_id: UUID
    title: str
    description: str
    type: str
    severity: str = "media"
    dimensions: list[str] = []
    node_ids: list[str] = []
    confidence: float = 0.5
    confidence_rationale: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# 7. Recommendation  (Paso 4 — recomendaciones de síntesis ejecutiva)
# ─────────────────────────────────────────────────────────────────────────────

class Recommendation(SQLModel, table=True):
    __tablename__ = "recommendations"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, nullable=False),
    )
    run_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    org_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    finding_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("findings.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    title: str = Field(
        sa_column=Column(String(500), nullable=False),
    )
    description: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    # 1 = más urgente
    priority: int = Field(
        default=99,
        sa_column=Column(Integer, nullable=False, server_default="99"),
    )
    # bajo | medio | alto
    impact: str = Field(
        default="medio",
        sa_column=Column(String(10), nullable=False, server_default="medio"),
    )
    # bajo | medio | alto
    effort: str = Field(
        default="medio",
        sa_column=Column(String(10), nullable=False, server_default="medio"),
    )
    # inmediato | corto | mediano | largo
    horizon: str = Field(
        default="corto",
        sa_column=Column(String(15), nullable=False, server_default="corto"),
    )
    node_ids: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class RecommendationRead(SQLModel):
    id: UUID
    run_id: UUID
    org_id: UUID
    finding_id: UUID | None
    title: str
    description: str
    priority: int
    impact: str
    effort: str
    horizon: str
    node_ids: list[Any]
    created_at: datetime


class RecommendationCreate(SQLModel):
    run_id: UUID
    org_id: UUID
    finding_id: UUID | None = None
    title: str
    description: str
    priority: int = 99
    impact: str = "medio"
    effort: str = "medio"
    horizon: str = "corto"
    node_ids: list[str] = []


# ─────────────────────────────────────────────────────────────────────────────
# 8. EvidenceLink  (trazabilidad hallazgo → node_analysis / group_analysis)
# ─────────────────────────────────────────────────────────────────────────────

class EvidenceLink(SQLModel, table=True):
    __tablename__ = "evidence_links"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, nullable=False),
    )
    finding_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("findings.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    node_analysis_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("node_analyses.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    group_analysis_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("group_analyses.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    quote: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    # quantitative | qualitative | documentary
    evidence_type: str = Field(
        sa_column=Column(String(20), nullable=False),
    )


class EvidenceLinkRead(SQLModel):
    id: UUID
    finding_id: UUID
    node_analysis_id: UUID | None
    group_analysis_id: UUID | None
    quote: str | None
    evidence_type: str


class EvidenceLinkCreate(SQLModel):
    finding_id: UUID
    node_analysis_id: UUID | None = None
    group_analysis_id: UUID | None = None
    quote: str | None = None
    evidence_type: str
