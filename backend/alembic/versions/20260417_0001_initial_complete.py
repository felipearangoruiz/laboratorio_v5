"""initial complete schema — consolidación de todas las migraciones previas

Revision ID: 20260417_0001
Revises:
Create Date: 2026-04-17 20:00:00

Esta migración crea el esquema completo del producto desde cero, reflejando
todos los campos actuales de los modelos SQLModel. Reemplaza las 8 migraciones
anteriores (0001 → 0008) que estaban fragmentadas y tenían problemas de
idempotencia con enums.

Patrón de idempotencia:
- Todos los ENUMs se crean con raw SQL `DO $$ ... IF NOT EXISTS ...` para
  poder correr sobre bases de datos que ya tengan el tipo.
- Las columnas que usan enum nativo se declaran con `create_type=False` para
  que SQLAlchemy no intente re-crearlo al crear la tabla.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260417_0001"
down_revision = None
branch_labels = None
depends_on = None


# ══════════════════════════════════════════════════════════════════════════════
# ENUM types — declarados explícitamente con create_type=False
# ══════════════════════════════════════════════════════════════════════════════

user_role = postgresql.ENUM(
    "superadmin", "admin",
    name="user_role",
    create_type=False,
)

member_token_status = postgresql.ENUM(
    "pending", "in_progress", "completed", "expired",
    name="member_token_status",
    create_type=False,
)

quick_assessment_status = postgresql.ENUM(
    "waiting", "ready", "completed",
    name="quick_assessment_status",
    create_type=False,
)

processing_type = postgresql.ENUM(
    "ciego", "orientado", "orientacion",
    name="processing_type",
    create_type=False,
)

job_state = postgresql.ENUM(
    "pending", "running", "completed", "failed",
    name="job_state",
    create_type=False,
)


def _create_enum_if_not_exists(name: str, values: list[str]) -> None:
    """Crea un tipo ENUM de PostgreSQL solo si no existe (idempotente)."""
    values_sql = ", ".join(f"'{v}'" for v in values)
    op.execute(
        f"DO $$ BEGIN "
        f"IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='{name}') "
        f"THEN CREATE TYPE {name} AS ENUM ({values_sql}); "
        f"END IF; END $$;"
    )


def upgrade() -> None:
    # ─────────────────────────────────────────────────────────────────────
    # 0. ENUM types (idempotentes)
    # ─────────────────────────────────────────────────────────────────────
    _create_enum_if_not_exists("user_role", ["superadmin", "admin"])
    _create_enum_if_not_exists(
        "member_token_status",
        ["pending", "in_progress", "completed", "expired"],
    )
    _create_enum_if_not_exists(
        "quick_assessment_status",
        ["waiting", "ready", "completed"],
    )
    _create_enum_if_not_exists(
        "processing_type",
        ["ciego", "orientado", "orientacion"],
    )
    _create_enum_if_not_exists(
        "job_state",
        ["pending", "running", "completed", "failed"],
    )

    # ─────────────────────────────────────────────────────────────────────
    # 1. organizations (sin FK a users — circular, se agrega al final)
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(), nullable=False, server_default=""),
        sa.Column("sector", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("strategic_objectives", sa.String(), nullable=False, server_default=""),
        sa.Column("strategic_concerns", sa.String(), nullable=False, server_default=""),
        sa.Column("key_questions", sa.String(), nullable=False, server_default=""),
        sa.Column("additional_context", sa.String(), nullable=False, server_default=""),
        sa.Column(
            "org_structure_type",
            sa.String(length=20),
            nullable=False,
            server_default="areas",
        ),
        sa.Column("admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
    )

    # ─────────────────────────────────────────────────────────────────────
    # 2. users
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False, server_default="admin"),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_users_organization_id_organizations",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)

    # FK circular: organizations.admin_id → users.id
    op.create_foreign_key(
        "fk_organizations_admin_id_users",
        "organizations",
        "users",
        ["admin_id"],
        ["id"],
    )

    # ─────────────────────────────────────────────────────────────────────
    # 3. groups (canvas nodes — jerárquica con self-reference)
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        "groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "node_type",
            sa.String(length=20),
            nullable=False,
            server_default="area",
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(), nullable=False, server_default=""),
        sa.Column("tarea_general", sa.String(), nullable=False, server_default=""),
        sa.Column("email", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("area", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("nivel_jerarquico", sa.Integer(), nullable=True),
        sa.Column("tipo_nivel", sa.String(length=255), nullable=True),
        sa.Column("position_x", sa.Float(), nullable=False, server_default="0"),
        sa.Column("position_y", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_groups_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_group_id"],
            ["groups.id"],
            name="fk_groups_parent_group_id_groups",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_groups"),
    )

    # ─────────────────────────────────────────────────────────────────────
    # 4. members
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        "members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role_label", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("interview_token", sa.String(length=32), nullable=False),
        sa.Column(
            "token_status",
            member_token_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
            name="fk_members_group_id_groups",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_members_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_members"),
        sa.UniqueConstraint("interview_token", name="uq_members_interview_token"),
    )
    op.create_index(
        "ix_members_interview_token",
        "members",
        ["interview_token"],
        unique=False,
    )

    # ─────────────────────────────────────────────────────────────────────
    # 5. interviews (premium flow)
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        "interviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
            name="fk_interviews_group_id_groups",
        ),
        sa.ForeignKeyConstraint(
            ["member_id"],
            ["members.id"],
            name="fk_interviews_member_id_members",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_interviews_organization_id_organizations",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_interviews"),
        sa.UniqueConstraint("member_id", name="uq_interviews_member_id"),
    )

    # ─────────────────────────────────────────────────────────────────────
    # 6. lateral_relations (relaciones horizontales en el canvas)
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        "lateral_relations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "type",
            sa.String(length=50),
            nullable=False,
            server_default="colaboracion",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_lateral_relations_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_node_id"],
            ["groups.id"],
            name="fk_lateral_relations_source_node_id_groups",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_node_id"],
            ["groups.id"],
            name="fk_lateral_relations_target_node_id_groups",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_lateral_relations"),
    )

    # ─────────────────────────────────────────────────────────────────────
    # 7. memberships (reemplaza relación directa User-Organization)
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        "memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "role",
            sa.String(length=20),
            nullable=False,
            server_default="admin",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name="fk_memberships_org_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_memberships_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_memberships"),
        sa.UniqueConstraint("user_id", "org_id", name="uq_memberships_user_org"),
    )

    # ─────────────────────────────────────────────────────────────────────
    # 8. quick_assessments (flujo free — owner opcional, anónimo hasta registro)
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        "quick_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("org_name", sa.String(length=255), nullable=False),
        sa.Column("org_type", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("size_range", sa.String(length=50), nullable=False, server_default=""),
        sa.Column(
            "leader_responses",
            postgresql.JSON(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "scores",
            postgresql.JSON(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("member_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("responses_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status",
            quick_assessment_status,
            nullable=False,
            server_default="waiting",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name="fk_quick_assessments_owner_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_quick_assessments"),
    )

    # ─────────────────────────────────────────────────────────────────────
    # 9. quick_assessment_members
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        "quick_assessment_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("token", sa.String(length=32), nullable=False),
        sa.Column(
            "responses",
            postgresql.JSON(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["quick_assessments.id"],
            name="fk_quick_assessment_members_assessment_id_quick_assessments",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_quick_assessment_members"),
        sa.UniqueConstraint("token", name="uq_quick_assessment_members_token"),
    )
    op.create_index(
        "ix_quick_assessment_members_token",
        "quick_assessment_members",
        ["token"],
        unique=False,
    )
    op.create_index(
        "ix_quick_assessment_members_assessment_id",
        "quick_assessment_members",
        ["assessment_id"],
    )

    # ─────────────────────────────────────────────────────────────────────
    # 10. diagnosis_results (resultados del pipeline de IA)
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        "diagnosis_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="running",
        ),
        sa.Column(
            "scores",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "narrative",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "network_metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_diagnosis_results_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_diagnosis_results"),
    )

    # ─────────────────────────────────────────────────────────────────────
    # 11. processing_results (modelo legacy, aún importado en routers)
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        "processing_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("type", processing_type, nullable=False),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
            name="fk_processing_results_group_id_groups",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_processing_results_organization_id_organizations",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_processing_results"),
    )

    # ─────────────────────────────────────────────────────────────────────
    # 12. job_statuses (modelo legacy para tracking de jobs async)
    # ─────────────────────────────────────────────────────────────────────
    op.create_table(
        "job_statuses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", job_state, nullable=False, server_default="pending"),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_job_statuses_organization_id_organizations",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_job_statuses"),
    )


def downgrade() -> None:
    # DROP en orden inverso (respetando FKs)
    op.drop_table("job_statuses")
    op.drop_table("processing_results")
    op.drop_table("diagnosis_results")
    op.drop_index(
        "ix_quick_assessment_members_assessment_id",
        table_name="quick_assessment_members",
    )
    op.drop_index(
        "ix_quick_assessment_members_token",
        table_name="quick_assessment_members",
    )
    op.drop_table("quick_assessment_members")
    op.drop_table("quick_assessments")
    op.drop_table("memberships")
    op.drop_table("lateral_relations")
    op.drop_table("interviews")
    op.drop_index("ix_members_interview_token", table_name="members")
    op.drop_table("members")
    op.drop_table("groups")
    op.drop_constraint(
        "fk_organizations_admin_id_users",
        "organizations",
        type_="foreignkey",
    )
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("organizations")

    # DROP ENUM types (idempotente)
    op.execute("DROP TYPE IF EXISTS job_state;")
    op.execute("DROP TYPE IF EXISTS processing_type;")
    op.execute("DROP TYPE IF EXISTS quick_assessment_status;")
    op.execute("DROP TYPE IF EXISTS member_token_status;")
    op.execute("DROP TYPE IF EXISTS user_role;")
