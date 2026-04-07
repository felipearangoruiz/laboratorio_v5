"""initial models

Revision ID: 20260406_0001
Revises:
Create Date: 2026-04-06 00:00:01

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260406_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN CREATE TYPE user_role AS ENUM ('superadmin', 'admin'); END IF; END $$;"))
    bind.execute(sa.text("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'member_token_status') THEN CREATE TYPE member_token_status AS ENUM ('pending', 'in_progress', 'completed', 'expired'); END IF; END $$;"))
    bind.execute(sa.text("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'processing_type') THEN CREATE TYPE processing_type AS ENUM ('ciego', 'orientado', 'orientacion'); END IF; END $$;"))
    bind.execute(sa.text("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'job_state') THEN CREATE TYPE job_state AS ENUM ('pending', 'running', 'completed', 'failed'); END IF; END $$;"))

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
        sa.Column("role", sa.Text(), nullable=False, server_default="admin"),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_users_organization_id_organizations"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    bind.execute(sa.text("ALTER TABLE users ALTER COLUMN role DROP DEFAULT"))
    bind.execute(sa.text("ALTER TABLE users ALTER COLUMN role TYPE user_role USING role::user_role"))
    bind.execute(sa.text("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'admin'::user_role"))
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    op.create_foreign_key(op.f("fk_organizations_admin_id_users"), "organizations", "users", ["admin_id"], ["id"])

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
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_groups_organization_id_organizations"), ondelete="CASCADE"),
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
        sa.Column("token_status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], name=op.f("fk_members_group_id_groups"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_members_organization_id_organizations"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_members")),
        sa.UniqueConstraint("interview_token", name=op.f("uq_members_interview_token")),
    )
    bind.execute(sa.text("ALTER TABLE members ALTER COLUMN token_status DROP DEFAULT"))
    bind.execute(sa.text("ALTER TABLE members ALTER COLUMN token_status TYPE member_token_status USING token_status::member_token_status"))
    bind.execute(sa.text("ALTER TABLE members ALTER COLUMN token_status SET DEFAULT 'pending'::member_token_status"))
    op.create_index(op.f("ix_members_interview_token"), "members", ["interview_token"], unique=False)

    op.create_table(
        "interviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], name=op.f("fk_interviews_group_id_groups")),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], name=op.f("fk_interviews_member_id_members"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_interviews_organization_id_organizations")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interviews")),
        sa.UniqueConstraint("member_id", name=op.f("uq_interviews_member_id")),
    )

    op.create_table(
        "processing_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], name=op.f("fk_processing_results_group_id_groups")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_processing_results_organization_id_organizations")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_processing_results")),
    )
    bind.execute(sa.text("ALTER TABLE processing_results ALTER COLUMN type TYPE processing_type USING type::processing_type"))

    op.create_table(
        "job_statuses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_job_statuses_organization_id_organizations")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_statuses")),
    )
    bind.execute(sa.text("ALTER TABLE job_statuses ALTER COLUMN status DROP DEFAULT"))
    bind.execute(sa.text("ALTER TABLE job_statuses ALTER COLUMN status TYPE job_state USING status::job_state"))
    bind.execute(sa.text("ALTER TABLE job_statuses ALTER COLUMN status SET DEFAULT 'pending'::job_state"))


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
    bind.execute(sa.text("DROP TYPE IF EXISTS job_state"))
    bind.execute(sa.text("DROP TYPE IF EXISTS processing_type"))
    bind.execute(sa.text("DROP TYPE IF EXISTS member_token_status"))
    bind.execute(sa.text("DROP TYPE IF EXISTS user_role"))
