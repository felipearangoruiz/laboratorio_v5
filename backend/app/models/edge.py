from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlmodel import Field, SQLModel


class EdgeType(str, Enum):
    LATERAL = "lateral"
    PROCESS = "process"


class Edge(SQLModel, table=True):
    __tablename__ = "edges"

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
    source_node_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("nodes.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    target_node_id: UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("nodes.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    edge_type: EdgeType = Field(
        default=EdgeType.LATERAL,
        sa_column=Column(
            SAEnum(
                EdgeType,
                name="edge_type_enum",
                native_enum=True,
                create_type=False,
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
            server_default=EdgeType.LATERAL.value,
        ),
    )
    edge_metadata: dict = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="'{}'"),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    deleted_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )


class EdgeRead(SQLModel):
    id: UUID
    organization_id: UUID
    source_node_id: UUID
    target_node_id: UUID
    edge_type: EdgeType
    edge_metadata: dict
    created_at: datetime
    deleted_at: datetime | None
