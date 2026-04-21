from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Enum as SAEnum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlmodel import Field, SQLModel


class NodeType(str, Enum):
    UNIT = "unit"
    PERSON = "person"


class Node(SQLModel, table=True):
    __tablename__ = "nodes"

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
    parent_node_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("nodes.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    type: NodeType = Field(
        default=NodeType.UNIT,
        sa_column=Column(
            SAEnum(
                NodeType,
                name="node_type_enum",
                native_enum=True,
                create_type=False,
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
            server_default=NodeType.UNIT.value,
        ),
    )
    name: str = Field(sa_column=Column(String(255), nullable=False))
    position_x: float = Field(
        default=0.0,
        sa_column=Column(Float, nullable=False, server_default="0"),
    )
    position_y: float = Field(
        default=0.0,
        sa_column=Column(Float, nullable=False, server_default="0"),
    )
    attrs: dict = Field(
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


class NodeRead(SQLModel):
    id: UUID
    organization_id: UUID
    parent_node_id: UUID | None
    type: NodeType
    name: str
    position_x: float
    position_y: float
    attrs: dict
    created_at: datetime
    deleted_at: datetime | None
