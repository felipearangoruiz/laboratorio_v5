"""Add node_id to documents (scoped files per Node).

Sprint 2.B Commit 6a. Documentos ahora pueden asociarse a un Node específico
(además de la org). Incluye trigger PL/pgSQL que garantiza consistencia
documents.organization_id == nodes.organization_id del node referenciado.

Revision ID: 20260422_0011
Revises: 20260422_0010
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260422_0011"
down_revision = "20260422_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("nodes.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_documents_node_id", "documents", ["node_id"])

    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_check_document_node_same_org()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.node_id IS NOT NULL THEN
                IF NOT EXISTS (
                    SELECT 1 FROM nodes
                    WHERE id = NEW.node_id
                      AND organization_id = NEW.organization_id
                ) THEN
                    RAISE EXCEPTION
                        'documents.organization_id (%) must match nodes.organization_id of referenced node (%)',
                        NEW.organization_id, NEW.node_id;
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_documents_node_same_org
        BEFORE INSERT OR UPDATE ON documents
        FOR EACH ROW EXECUTE FUNCTION fn_check_document_node_same_org();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_documents_node_same_org ON documents;")
    op.execute("DROP FUNCTION IF EXISTS fn_check_document_node_same_org();")
    op.drop_index("ix_documents_node_id", table_name="documents")
    op.drop_column("documents", "node_id")
