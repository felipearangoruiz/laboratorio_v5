"""backfill_interview_data.py

Sprint 1, gap fix post-Prompt 1.2.
Copia interviews.data → node_states.interview_data para los NodeStates
migrados en el Sprint 1.2 que quedaron sin datos de respuesta.

CONTEXTO
========
El Sprint 1.1 omitió la columna interview_data en NodeState (gap detectado
durante el 1.2). La migración Alembic 20260421_0008 la agrega como nullable.
Este script backfillea los datos existentes.

MATCHING KEY
============
Durante el Sprint 1.2, los UUIDs se preservaron:
    Member.id → Node.id (type=person)
    Interview.id → NodeState.id
    Interview.member_id = Member.id = NodeState.node_id

Por lo tanto: interviews.member_id == node_states.node_id es la join key.

IDEMPOTENCIA
============
Si node_states.interview_data ya tiene contenido (no NULL), el NodeState
se salta sin error. Permite re-ejecución segura.

VALIDACIÓN FINAL
================
Los interviews con submitted_at IS NOT NULL deben corresponder exactamente
a node_states con interview_data IS NOT NULL y status IN ('completed').

EJECUCIÓN
=========
    # Dry-run (sin --apply): ejecuta todo, valida, hace ROLLBACK.
    docker compose exec backend uv run python scripts/backfill_interview_data.py

    # Aplicación real:
    docker compose exec backend uv run python scripts/backfill_interview_data.py --apply
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlalchemy import text  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from app.db import engine  # noqa: E402
from app.models.interview import Interview  # noqa: E402
from app.models.node_state import NodeState  # noqa: E402

_SCRIPTS_DIR = Path(__file__).resolve().parent
NOW_UTC = datetime.now(timezone.utc)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill interview_data en node_states desde la tabla interviews legacy."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Ejecuta COMMIT real. Sin este flag hace ROLLBACK al final (dry-run).",
    )
    args = parser.parse_args()
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[backfill] {mode} — {NOW_UTC.isoformat()}")
    print("=" * 60)

    with Session(engine) as session:
        # ── Pre-check: verificar que interview_data existe en la tabla ───
        conn = session.connection()
        col_exists = conn.execute(
            text("""
                SELECT COUNT(*) FROM information_schema.columns
                WHERE table_name = 'node_states'
                  AND column_name = 'interview_data'
            """)
        ).scalar_one()
        if not col_exists:
            print(
                "[backfill] ❌ ABORT: columna node_states.interview_data no existe. "
                "Ejecutar la migración 20260421_0008 primero."
            )
            return 1

        # ── Snapshot pre-backfill ─────────────────────────────────────────
        total_interviews = conn.execute(
            text("SELECT COUNT(*) FROM interviews")
        ).scalar_one()
        total_node_states = conn.execute(
            text("SELECT COUNT(*) FROM node_states")
        ).scalar_one()
        already_filled = conn.execute(
            text("SELECT COUNT(*) FROM node_states WHERE interview_data IS NOT NULL")
        ).scalar_one()
        submitted_count = conn.execute(
            text("SELECT COUNT(*) FROM interviews WHERE submitted_at IS NOT NULL")
        ).scalar_one()

        print(f"\n## SNAPSHOT INICIAL")
        print(f"  interviews (total):                {total_interviews}")
        print(f"  node_states (total):               {total_node_states}")
        print(f"  node_states con interview_data:    {already_filled}")
        print(f"  interviews con submitted_at:       {submitted_count}")

        # ── Load all interviews and build lookup: member_id → interview ──
        interviews = list(session.exec(select(Interview)).all())
        iv_by_member: dict = {iv.member_id: iv for iv in interviews}

        # Detect duplicates (should not exist — member_id UNIQUE on interviews)
        if len(iv_by_member) != len(interviews):
            print(
                "[backfill] ❌ ABORT: se detectaron interviews duplicadas por member_id. "
                "Violación del contrato del Sprint 1.2. No se aplica el backfill."
            )
            session.rollback()
            return 1

        # ── Load all NodeStates ───────────────────────────────────────────
        node_states = list(session.exec(select(NodeState)).all())

        updated = 0
        skipped_idempotent = 0
        skipped_no_interview = 0
        interviews_without_node_state = []

        print(f"\n## BACKFILL")

        for ns in node_states:
            # Idempotency: skip if already has data
            if ns.interview_data is not None:
                skipped_idempotent += 1
                print(f"  SKIP  (ya tiene datos) NodeState {ns.id} node={ns.node_id}")
                continue

            iv = iv_by_member.get(ns.node_id)
            if iv is None:
                # Legitimate: person was invited but never had an interview record
                skipped_no_interview += 1
                print(f"  SKIP  (sin interview) NodeState {ns.id} node={ns.node_id}")
                continue

            # Copy interview.data → node_state.interview_data
            ns.interview_data = iv.data
            session.add(ns)
            print(
                f"  UPDATE NodeState {ns.id} node={ns.node_id} "
                f"data_keys={list(iv.data.keys()) if isinstance(iv.data, dict) else '?'}"
            )
            updated += 1

        print(f"\n  → {updated} actualizados, "
              f"{skipped_idempotent} saltados (idempotentes), "
              f"{skipped_no_interview} saltados (sin interview).")

        # ── Check: every interview should have a matching NodeState ──────
        for iv in interviews:
            # Find NodeState by node_id = member_id (the UUID-preserved link)
            ns_match = next(
                (ns for ns in node_states if ns.node_id == iv.member_id), None
            )
            if ns_match is None:
                interviews_without_node_state.append(iv.id)

        if interviews_without_node_state:
            session.rollback()
            print(
                f"\n[backfill] ❌ ABORT: {len(interviews_without_node_state)} interview(s) "
                f"sin NodeState correspondiente — violación del contrato del Sprint 1.2:\n"
                + "\n".join(f"  interview.id={iv_id}" for iv_id in interviews_without_node_state)
            )
            return 1

        # ── Flush to make updates visible for validation ─────────────────
        session.flush()

        # ── Validación final ──────────────────────────────────────────────
        print("\n## VALIDACIÓN FINAL")
        conn2 = session.connection()

        n_submitted = conn2.execute(
            text("SELECT COUNT(*) FROM interviews WHERE submitted_at IS NOT NULL")
        ).scalar_one()
        n_with_data = conn2.execute(
            text(
                "SELECT COUNT(*) FROM node_states "
                "WHERE interview_data IS NOT NULL AND status = 'completed'"
            )
        ).scalar_one()

        val_ok = n_submitted == n_with_data
        icon = "✅" if val_ok else "❌"
        print(
            f"  {icon} interviews[submitted] == node_states[data+completed]: "
            f"{n_submitted} == {n_with_data}"
        )

        if not val_ok:
            session.rollback()
            print(
                f"\n[backfill] ❌ ROLLBACK: validación fallida — "
                f"interviews con submitted_at={n_submitted} "
                f"≠ node_states con interview_data+completed={n_with_data}"
            )
            return 1

        # ── Commit or rollback ────────────────────────────────────────────
        if args.apply:
            session.commit()
            print(f"\n✅ COMMIT: {updated} node_states actualizados.")
        else:
            session.rollback()
            print(
                f"\n⚠️  DRY-RUN: validación pasó. "
                f"Ejecutar con --apply para aplicar el backfill real."
            )

    print("\n## RESUMEN FINAL")
    print(f"  Modo: {mode} | Estado: OK")
    print(f"  Actualizados:              {updated}")
    print(f"  Saltados (idempotentes):   {skipped_idempotent}")
    print(f"  Saltados (sin interview):  {skipped_no_interview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
