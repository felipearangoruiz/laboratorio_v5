"""invariantes_db

Revision ID: 20260421_0009
Revises: 20260421_0008
Create Date: 2026-04-21

Sprint 2.1 — Migra invariantes 2, 3, 4, 6 y 11 de MODEL_PHILOSOPHY.md §8
del nivel router (Nivel 1) al nivel DB (Nivel 2) via CHECK constraints,
partial UNIQUE index y triggers PL/pgSQL.

Cierra el agujero del compat layer del Sprint 1.4: los routers legacy
(groups.py, members.py, interviews.py, interview_public.py) ahora son
frenados por la DB si algun dia intentan materializar datos invalidos.

Invariantes cubiertas aqui:
  - 2: parent_node_id misma org (trigger).
  - 3: unit no puede tener parent person (trigger).
  - 4: edge source != target (CHECK).
  - 6: edge con nodes misma org (trigger).
  - 11: una Campaign active por org (partial unique index).

Ya cubiertas en Sprint 1.1 (no se duplican aqui):
  - 1: organization_id NOT NULL en Node.
  - 10: UNIQUE (node_id, campaign_id) en NodeState.

NO se migran en este sprint:
  - 5, 8, 9, 12, 13: validacion semantica/acyclic/JSONB -> siguen en router.
  - 7: conflicto documental vs Sprint 1.1 (edge_metadata.order distingue
    duplicados legitimos de process edges). Decision pendiente.
"""
from __future__ import annotations

from alembic import op

# revision identifiers
revision = "20260421_0009"
down_revision = "20260421_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Invariante 2 — parent_node_id misma organizacion
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_check_node_parent_same_org()
        RETURNS TRIGGER AS $$
        DECLARE
            parent_org UUID;
        BEGIN
            IF NEW.parent_node_id IS NOT NULL THEN
                SELECT organization_id INTO parent_org
                FROM nodes WHERE id = NEW.parent_node_id;
                IF parent_org IS NULL THEN
                    RAISE EXCEPTION
                        'Invariante 2: parent_node_id % no existe',
                        NEW.parent_node_id;
                END IF;
                IF parent_org != NEW.organization_id THEN
                    RAISE EXCEPTION
                        'Invariante 2: parent_node_id % pertenece a org % pero node pertenece a org %',
                        NEW.parent_node_id, parent_org, NEW.organization_id;
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_nodes_parent_same_org
        BEFORE INSERT OR UPDATE ON nodes
        FOR EACH ROW EXECUTE FUNCTION fn_check_node_parent_same_org();
        """
    )

    # ------------------------------------------------------------------
    # Invariante 3 — unit no puede tener parent person
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_check_unit_parent_is_unit()
        RETURNS TRIGGER AS $$
        DECLARE
            parent_type node_type_enum;
        BEGIN
            IF NEW.type = 'unit' AND NEW.parent_node_id IS NOT NULL THEN
                SELECT type INTO parent_type
                FROM nodes WHERE id = NEW.parent_node_id;
                IF parent_type IS NULL THEN
                    RAISE EXCEPTION
                        'Invariante 3: parent_node_id % no existe',
                        NEW.parent_node_id;
                END IF;
                IF parent_type != 'unit' THEN
                    RAISE EXCEPTION
                        'Invariante 3: un unit no puede tener parent de tipo % (parent_node_id=%)',
                        parent_type, NEW.parent_node_id;
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_nodes_unit_parent_is_unit
        BEFORE INSERT OR UPDATE ON nodes
        FOR EACH ROW EXECUTE FUNCTION fn_check_unit_parent_is_unit();
        """
    )

    # ------------------------------------------------------------------
    # Invariante 4 — edge source != target
    # ------------------------------------------------------------------
    op.execute(
        """
        ALTER TABLE edges
        ADD CONSTRAINT check_edge_source_ne_target
        CHECK (source_node_id != target_node_id);
        """
    )

    # ------------------------------------------------------------------
    # Invariante 6 — edge nodes misma organizacion
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_check_edge_nodes_same_org()
        RETURNS TRIGGER AS $$
        DECLARE
            src_org UUID;
            tgt_org UUID;
        BEGIN
            SELECT organization_id INTO src_org
            FROM nodes WHERE id = NEW.source_node_id;
            SELECT organization_id INTO tgt_org
            FROM nodes WHERE id = NEW.target_node_id;
            IF src_org IS NULL THEN
                RAISE EXCEPTION
                    'Invariante 6: source_node_id % no existe',
                    NEW.source_node_id;
            END IF;
            IF tgt_org IS NULL THEN
                RAISE EXCEPTION
                    'Invariante 6: target_node_id % no existe',
                    NEW.target_node_id;
            END IF;
            IF src_org != NEW.organization_id THEN
                RAISE EXCEPTION
                    'Invariante 6: source_node_id pertenece a org % pero edge pertenece a org %',
                    src_org, NEW.organization_id;
            END IF;
            IF tgt_org != NEW.organization_id THEN
                RAISE EXCEPTION
                    'Invariante 6: target_node_id pertenece a org % pero edge pertenece a org %',
                    tgt_org, NEW.organization_id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_edges_nodes_same_org
        BEFORE INSERT OR UPDATE ON edges
        FOR EACH ROW EXECUTE FUNCTION fn_check_edge_nodes_same_org();
        """
    )

    # ------------------------------------------------------------------
    # Invariante 11 — una Campaign active por org
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE UNIQUE INDEX uniq_one_active_campaign_per_org
        ON assessment_campaigns (organization_id)
        WHERE status = 'active';
        """
    )


def downgrade() -> None:
    # Invariante 11
    op.execute("DROP INDEX IF EXISTS uniq_one_active_campaign_per_org;")

    # Invariante 6
    op.execute("DROP TRIGGER IF EXISTS trg_edges_nodes_same_org ON edges;")
    op.execute("DROP FUNCTION IF EXISTS fn_check_edge_nodes_same_org();")

    # Invariante 4
    op.execute(
        "ALTER TABLE edges DROP CONSTRAINT IF EXISTS check_edge_source_ne_target;"
    )

    # Invariante 3
    op.execute("DROP TRIGGER IF EXISTS trg_nodes_unit_parent_is_unit ON nodes;")
    op.execute("DROP FUNCTION IF EXISTS fn_check_unit_parent_is_unit();")

    # Invariante 2
    op.execute("DROP TRIGGER IF EXISTS trg_nodes_parent_same_org ON nodes;")
    op.execute("DROP FUNCTION IF EXISTS fn_check_node_parent_same_org();")
