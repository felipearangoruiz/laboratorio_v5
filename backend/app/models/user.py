from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel


class UserRole(str, Enum):
    SUPERADMIN = "SUPERADMIN"
    ADMIN = "ADMIN"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, nullable=False),
    )
    email: str = Field(nullable=False, index=True, unique=True, max_length=255)
    hashed_password: str = Field(nullable=False, max_length=255)
    role: UserRole = Field(
        default=UserRole.ADMIN,
        sa_column=Column(
            SAEnum(UserRole, name="user_role", native_enum=True, create_type=False),
            nullable=False,
            server_default=UserRole.ADMIN.value,
        ),
    )
    organization_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class UserRead(SQLModel):
    id: UUID
    email: str
    role: UserRole
    organization_id: UUID | None
    created_at: datetime
