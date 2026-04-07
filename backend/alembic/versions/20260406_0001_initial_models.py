"""initial models

Revision ID: 20260406_0001
Revises:
Create Date: 2026-04-06 00:00:01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260406_0001"
down_revision = None
branch_labels = None
depends_on = None

user_role = sa.Enum("superadmin", "admin", name="user_role", create_type=False)
member_token_status = sa.Enum(
    "pending",
    "in_progress",
    "completed",
    "expired",
    name="member_token_status",
    create_type=False,
)
processing_type = sa.Enum(
    "ciego", "orientado", "orientacion", name="processing_type", create_type=False
)
job_state = sa.Enum(
    "pending", "running", "completed", "failed", name="job_state", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)
    member_token_status.create(bind, checkfirst=True)
    processing_type.create(bind, checkfirst=True)
    job_state.create(bind, checkfirst=True)

    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(), nullable=False, server_default=""),
        sa.Column("sector", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("superadmin", "admin", name="user_role", create_type=False),
            nullable=False,
            server_default="admin",
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_users_organization_id_organizations"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    op.create_foreign_key(
        op.f("fk_organizations_admin_id_users"),
        "organizations",
        "users",
        ["admin_id"],
        ["id"],
    )

    op.create_table(
        "groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(), nullable=False, server_default=""),
        sa.Column("tarea_general", sa.String(), nullable=False, server_default=""),
        sa.Column("nivel_jerarquico", sa.Integer(), nullable=True),
        sa.Column("tipo_nivel", sa.String(length=255), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_groups_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_groups")),
    )

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
            sa.Enum(
                "pending",
                "in_progress",
                "completed",
                "expired",
                name="member_token_status",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
            name=op.f("fk_members_group_id_groups"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_members_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_members")),
        sa.UniqueConstraint("interview_token", name=op.f("uq_members_interview_token")),
    )
    op.create_index(
        op.f("ix_members_interview_token"), "members", ["interview_token"], unique=False
    )

    op.create_table(
        "interviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
            name=op.f("fk_interviews_group_id_groups"),
        ),
        sa.ForeignKeyConstraint(
            ["member_id"],
            ["members.id"],
            name=op.f("fk_interviews_member_id_members"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_interviews_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interviews")),
        sa.UniqueConstraint("member_id", name=op.f("uq_interviews_member_id")),
    )

    op.create_table(
        "processing_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "type",
            sa.Enum(
                "ciego",
                "orientado",
                "orientacion",
                name="processing_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
            name=op.f("fk_processing_results_group_id_groups"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_processing_results_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_processing_results")),
    )

    op.create_table(
        "job_statuses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "completed",
                "failed",
                name="job_state",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_job_statuses_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_statuses")),
    )


def downgrade() -> None:
    op.drop_table("job_statuses")
    op.drop_table("processing_results")
    op.drop_table("interviews")
    op.drop_index(op.f("ix_members_interview_token"), table_name="members")
    op.drop_table("members")
    op.drop_table("groups")
    op.drop_constraint(op.f("fk_organizations_admin_id_users"), "organizations", type_="foreignkey")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_table("organizations")

    bind = op.get_bind()
    job_state.drop(bind, checkfirst=True)
    processing_type.drop(bind, checkfirst=True)
    member_token_status.drop(bind, checkfirst=True)
    user_role.drop(bind, checkfirst=True)
