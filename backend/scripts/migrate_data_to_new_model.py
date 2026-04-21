"""migrate_data_to_new_model.py

Sprint 1, Prompt 1.2.
Migra Group → Node(unit), Member → Node(person), Interview → NodeState.
Crea una AssessmentCampaign "Diagnóstico Inicial" por organización.
Implementa las decisiones D1–D8 del contrato versionado en commit 5b297d4.

COLUMN DIVERGENCES FROM TASK SPEC
==================================
Las siguientes columnas asumidas en la spec no existen en los modelos reales.
El mapeo adaptado se documenta aquí para trazabilidad:

Interview (spec → real):
  interview.started_at      NO EXISTE. Estado "in_progress" no es asignable.
                             Mapeo de status: submitted_at IS NOT NULL → "completed",
                             en caso contrario → "invited".
  interview.token           NO EXISTE en Interview. Se usa member.interview_token
                             como respondent_token del NodeState.
  interview.email_sent_to   NO EXISTE. email_assigned = NULL en todos los NodeStates.
  interview.invited_at      NO EXISTE. invited_at = member.created_at (mejor proxy).

NodeState (spec → real):
  interview_data (jsonb)    NO EXISTE en NodeState. interview.data no tiene columna
                             destino en el nuevo modelo; los datos de respuestas quedan
                             en la tabla legacy "interviews". Deuda documental pendiente
                             (agregar interview_data al NodeState o crear tabla propia
                             en un sprint posterior).

Node (spec → real):
  node.description          NO EXISTE. group.description se preserva en attrs["description"].
  node.updated_at           NO EXISTE en Node ni en Group. Campo omitido.

Member (spec → real):
  member.email              NO EXISTE en Member. Node.attrs = {} para persons
                             (sin email que preservar).

CONVENCIÓN DE EJECUCIÓN
========================
    # Dry-run (sin --apply): ejecuta todo, valida, hace ROLLBACK. Exit 0 si OK.
    docker compose exec backend uv run python scripts/migrate_data_to_new_model.py

    # Aplicación real:
    docker compose exec backend uv run python scripts/migrate_data_to_new_model.py --apply

SALIDAS
=======
    1. stdout
    2. scripts/migration_execution_report.md (o con timestamp si ya existe)
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlalchemy import text  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from app.db import engine  # noqa: E402
from app.models.campaign import AssessmentCampaign, CampaignStatus  # noqa: E402
from app.models.group import Group  # noqa: E402
from app.models.interview import Interview  # noqa: E402
from app.models.member import Member  # noqa: E402
from app.models.node import Node, NodeType  # noqa: E402
from app.models.node_state import NodeState, NodeStateStatus  # noqa: E402
from app.models.organization import Organization  # noqa: E402

# ─── Constants ────────────────────────────────────────────────────────────────

_SCRIPTS_DIR = Path(__file__).resolve().parent
REPORT_BASE = "migration_execution_report"
NOW_UTC = datetime.now(timezone.utc)

# D1 heuristic: role keywords that mark a person as standalone (parent_node_id = NULL)
STANDALONE_KEYWORDS = frozenset(
    {"asesor", "consultor", "externo", "proveedor", "contractor", "freelance"}
)

# Motor tables — counts must be identical before and after migration
MOTOR_TABLES = [
    "analysis_runs",
    "node_analyses",
    "group_analyses",
    "org_analyses",
    "findings",
    "recommendations",
    "evidence_links",
    "document_extractions",
]


# ─── Dual logging ─────────────────────────────────────────────────────────────

class DualLog:
    """Logs to stdout and accumulates lines for the markdown report."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def __call__(self, msg: str = "") -> None:
        print(msg)
        self.lines.append(msg)

    def write_report(self, apply_mode: bool) -> Path:
        base = _SCRIPTS_DIR / f"{REPORT_BASE}.md"
        if base.exists():
            ts = NOW_UTC.strftime("%Y%m%dT%H%M%S")
            path = _SCRIPTS_DIR / f"{REPORT_BASE}_{ts}.md"
        else:
            path = base
        mode_label = "APPLY" if apply_mode else "DRY-RUN"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"# Migration Execution Report ({mode_label})\n\n")
            fh.write(f"_Generated: {NOW_UTC.isoformat()} (UTC)_\n\n")
            fh.write("```\n")
            fh.write("\n".join(self.lines))
            fh.write("\n```\n")
        return path


# ─── Motor snapshot ───────────────────────────────────────────────────────────

def snapshot_motor_counts(session: Session) -> dict[str, int]:
    conn = session.connection()
    return {
        t: conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar_one()
        for t in MOTOR_TABLES
    }


# ─── Topological sort for Groups ──────────────────────────────────────────────

def topological_sort_groups(groups: list[Group]) -> list[Group]:
    """Sort groups parent-before-child using BFS from roots.

    Strategy chosen: topological sort (vs. two-pass insert-then-update).
    Reason: single pass, no UPDATE needed, cleaner transaction log.
    Orphaned groups (parent_group_id points to non-existent group) are
    appended at the end — this is an undocumented edge case that triggers
    a RuntimeError at insert time (no D decision covers it).
    """
    group_by_id: dict[UUID, Group] = {g.id: g for g in groups}
    children_of: dict[UUID, list[Group]] = defaultdict(list)
    roots: list[Group] = []

    for g in groups:
        if g.parent_group_id is None:
            roots.append(g)
        elif g.parent_group_id in group_by_id:
            children_of[g.parent_group_id].append(g)
        # else: orphaned parent — appended at end below

    result: list[Group] = []
    queue: deque[Group] = deque(sorted(roots, key=lambda g: g.created_at))
    while queue:
        g = queue.popleft()
        result.append(g)
        for child in sorted(children_of[g.id], key=lambda c: c.created_at):
            queue.append(child)

    # Orphaned groups (parent not in groups table) appended last
    seen = {g.id for g in result}
    for g in sorted(groups, key=lambda g: g.created_at):
        if g.id not in seen:
            result.append(g)

    return result


# ─── D7: auto-position grid ───────────────────────────────────────────────────

def compute_d7_positions(zero_groups: list[Group]) -> dict[UUID, tuple[float, float]]:
    """D7: assign deterministic grid positions to groups at (0,0), per org.

    Algorithm (from migration contract D7):
        N = ceil(sqrt(count_per_org))
        groups sorted by created_at asc within org
        x = 100 + (i % N) * 250
        y = 100 + (i // N) * 150
    """
    by_org: dict[UUID, list[Group]] = defaultdict(list)
    for g in zero_groups:
        by_org[g.organization_id].append(g)

    positions: dict[UUID, tuple[float, float]] = {}
    for org_groups in by_org.values():
        sorted_og = sorted(org_groups, key=lambda g: g.created_at)
        n = max(1, math.ceil(math.sqrt(len(sorted_og))))
        for i, g in enumerate(sorted_og):
            positions[g.id] = (
                100.0 + (i % n) * 250.0,
                100.0 + (i // n) * 150.0,
            )
    return positions


# ─── Part 1: AssessmentCampaigns ──────────────────────────────────────────────

def migrate_campaigns(
    session: Session, orgs: list[Organization], log: DualLog
) -> dict[UUID, UUID]:
    """Create 'Diagnóstico Inicial' campaign per org (idempotent).

    Returns dict org_id → campaign_id.
    D8: created_by_user_id = NULL (distinguishes migrated vs. native campaigns).
    """
    log("\n## PARTE 1 — AssessmentCampaigns")
    log(f"  Organizaciones: {len(orgs)}")
    org_to_campaign: dict[UUID, UUID] = {}
    created = skipped = 0
    conn = session.connection()

    for org in orgs:
        existing = session.exec(
            select(AssessmentCampaign).where(
                AssessmentCampaign.organization_id == org.id,
                AssessmentCampaign.name == "Diagnóstico Inicial",
            )
        ).first()
        if existing:
            log(f"  SKIP  [{org.name}] campaign ya existe ({existing.id})")
            org_to_campaign[org.id] = existing.id
            skipped += 1
            continue

        row = conn.execute(
            text("""
                SELECT MIN(i.submitted_at), MAX(i.submitted_at)
                FROM interviews i
                JOIN members m ON m.id = i.member_id
                WHERE m.organization_id = :oid AND i.submitted_at IS NOT NULL
            """),
            {"oid": str(org.id)},
        ).fetchone()

        if row and row[0] is not None:
            started_at, closed_at = row[0], row[1]
        else:
            started_at = closed_at = org.created_at

        cid = uuid4()
        session.add(AssessmentCampaign(
            id=cid,
            organization_id=org.id,
            created_by_user_id=None,          # D8
            name="Diagnóstico Inicial",
            status=CampaignStatus.CLOSED,
            started_at=started_at,
            closed_at=closed_at,
            created_at=NOW_UTC,
        ))
        org_to_campaign[org.id] = cid
        log(f"  CREATE [{org.name}] id={cid} started={started_at} closed={closed_at}")
        created += 1

    log(f"  → {created} creadas, {skipped} saltadas.")
    return org_to_campaign


# ─── Part 2: Groups → Nodes(unit) ─────────────────────────────────────────────

def migrate_groups_to_nodes(
    session: Session, groups: list[Group], log: DualLog
) -> dict[UUID, UUID]:
    """Migrate all Groups to Node(type=unit). Returns root_units_by_org.

    root_units_by_org: org_id → id of the oldest root-level unit node.
    Used as D1 fallback for members with no valid group assignment.
    Legacy fields (description, tarea_general, area, context_notes, is_default)
    have no column in Node — they are preserved in Node.attrs.
    """
    log("\n## PARTE 2 — Groups → Nodes (type=unit)")
    log(f"  Groups encontrados: {len(groups)}")

    group_ids = {g.id for g in groups}
    zero_groups = [g for g in groups if g.position_x == 0.0 and g.position_y == 0.0]
    d7_positions = compute_d7_positions(zero_groups)
    if d7_positions:
        log(f"  D7: {len(d7_positions)} grupo(s) con posición (0,0) → auto-grid")

    sorted_groups = topological_sort_groups(groups)

    # Track oldest root unit per org for D1 fallback
    root_units: dict[UUID, tuple[UUID, datetime]] = {}  # org_id → (node_id, created_at)
    created = skipped = 0

    for g in sorted_groups:
        existing = session.exec(select(Node).where(Node.id == g.id)).first()
        if existing:
            log(f"  SKIP  [{g.name}] Node {g.id} ya existe")
            if g.parent_group_id is None:
                _update_root(root_units, g.organization_id, g.id, g.created_at)
            skipped += 1
            continue

        # parent_node_id
        if g.parent_group_id is None:
            parent_node_id = None
        elif g.parent_group_id in group_ids:
            parent_node_id = g.parent_group_id
        else:
            raise RuntimeError(
                f"CASO NO DOCUMENTADO: Group {g.id} ({g.name!r}) tiene "
                f"parent_group_id={g.parent_group_id} que no existe en groups. "
                "Ninguna decisión D cubre este caso. Abortando."
            )

        # position (D7 if needed)
        if g.id in d7_positions:
            px, py = d7_positions[g.id]
            log(f"  D7    [{g.name}] ({g.position_x},{g.position_y}) → ({px},{py})")
        else:
            px, py = float(g.position_x), float(g.position_y)

        # attrs: preserve legacy fields that have no Node column
        attrs: dict = {}
        if g.description:
            attrs["description"] = g.description
        if g.tarea_general:
            attrs["tarea_general"] = g.tarea_general
        if g.area:
            attrs["area"] = g.area
        if g.context_notes:
            attrs["context_notes"] = g.context_notes
        if g.is_default:
            attrs["is_default"] = True
        if g.node_type != "area":
            attrs["legacy_node_type"] = g.node_type

        session.add(Node(
            id=g.id,
            organization_id=g.organization_id,
            parent_node_id=parent_node_id,
            type=NodeType.UNIT,
            name=g.name,
            position_x=px,
            position_y=py,
            attrs=attrs,
            created_at=g.created_at,
            deleted_at=None,
        ))

        if parent_node_id is None:
            _update_root(root_units, g.organization_id, g.id, g.created_at)

        log(f"  CREATE [{g.name}] id={g.id} parent={parent_node_id} pos=({px},{py})")
        created += 1

    log(f"  → {created} creados, {skipped} saltados.")
    return {org_id: data[0] for org_id, data in root_units.items()}


def _update_root(
    root_units: dict[UUID, tuple[UUID, datetime]],
    org_id: UUID,
    node_id: UUID,
    created_at: datetime,
) -> None:
    if org_id not in root_units or created_at < root_units[org_id][1]:
        root_units[org_id] = (node_id, created_at)


# ─── Part 3: Members → Nodes(person) ──────────────────────────────────────────

def migrate_members_to_nodes(
    session: Session,
    members: list[Member],
    root_units_by_org: dict[UUID, UUID],
    org_ids: set[UUID],
    group_ids: set[UUID],
    log: DualLog,
) -> tuple[int, int]:
    """Migrate Members to Node(type=person). Returns (created, discarded).

    Applies D1 (role heuristic) and D3 (orphan sub-rules).
    member.email does not exist → Node.attrs = {}.
    member.role_label goes to NodeState.role_label; attrs stays empty.
    """
    log("\n## PARTE 3 — Members → Nodes (type=person)")
    log(f"  Members encontrados: {len(members)}")
    created = discarded = 0
    # Track "General" fallback nodes created on-the-fly
    general_by_org: dict[UUID, UUID] = {}

    for m in members:
        existing = session.exec(select(Node).where(Node.id == m.id)).first()
        if existing:
            log(f"  SKIP  [{m.name}] Node {m.id} ya existe")
            continue

        # D3a: org doesn't exist
        if m.organization_id not in org_ids:
            log(f"  DISCARD D3a: member {m.id} ({m.name!r}) org {m.organization_id} no existe")
            discarded += 1
            continue

        # Determine parent_node_id
        if m.group_id is not None and m.group_id in group_ids:
            parent_node_id: UUID | None = m.group_id
        else:
            if m.group_id is not None:
                log(f"  D3b: member {m.id} group_id={m.group_id} no existe → heurística D1")
            role_lower = (m.role_label or "").lower()
            if any(kw in role_lower for kw in STANDALONE_KEYWORDS):
                parent_node_id = None
                log(f"  D1 standalone: {m.name!r} role={m.role_label!r}")
            else:
                parent_node_id = _ensure_root_unit(
                    session, m.organization_id, root_units_by_org, general_by_org, log
                )

        session.add(Node(
            id=m.id,
            organization_id=m.organization_id,
            parent_node_id=parent_node_id,
            type=NodeType.PERSON,
            name=m.name,
            position_x=0.0,
            position_y=0.0,
            attrs={},
            created_at=m.created_at,
            deleted_at=None,
        ))
        log(f"  CREATE [{m.name}] id={m.id} parent={parent_node_id}")
        created += 1

    log(f"  → {created} creados, {discarded} descartados (D3a).")
    return created, discarded


def _ensure_root_unit(
    session: Session,
    org_id: UUID,
    root_units_by_org: dict[UUID, UUID],
    general_by_org: dict[UUID, UUID],
    log: DualLog,
) -> UUID:
    """Return the root unit node id for the org, creating 'General' if needed."""
    if org_id in root_units_by_org:
        return root_units_by_org[org_id]
    if org_id in general_by_org:
        return general_by_org[org_id]
    # D1 fallback: create "General" unit node
    gid = uuid4()
    session.add(Node(
        id=gid,
        organization_id=org_id,
        parent_node_id=None,
        type=NodeType.UNIT,
        name="General",
        position_x=100.0,
        position_y=100.0,
        attrs={"migrated_auto_fallback": True},
        created_at=NOW_UTC,
        deleted_at=None,
    ))
    general_by_org[org_id] = gid
    root_units_by_org[org_id] = gid
    log(f"  D1 fallback: creado Node 'General' id={gid} para org {org_id}")
    return gid


# ─── Part 4: Interviews → NodeStates ──────────────────────────────────────────

def migrate_interviews_to_node_states(
    session: Session,
    interviews: list[Interview],
    org_to_campaign: dict[UUID, UUID],
    member_org_map: dict[UUID, UUID],
    member_token_map: dict[UUID, str],
    member_role_map: dict[UUID, str | None],
    member_created_map: dict[UUID, datetime],
    log: DualLog,
) -> tuple[int, int]:
    """Migrate Interviews to NodeStates (idempotent). Returns (created, discarded).

    Column divergences (see module docstring):
    - respondent_token  ← member.interview_token (interview.token doesn't exist)
    - email_assigned    = NULL (interview.email_sent_to doesn't exist)
    - invited_at        ← member.created_at proxy (interview.invited_at doesn't exist)
    - status            = "completed" if submitted_at IS NOT NULL else "invited"
                          ("in_progress" not assignable — interview.started_at doesn't exist)
    - interview_data    OMITTED — NodeState has no such column. interview.data stays
                          in the legacy table.
    """
    log("\n## PARTE 4 — Interviews → NodeStates")
    log(f"  Interviews encontradas: {len(interviews)}")
    log("  [Adaptaciones de schema activas — ver docstring del módulo]")
    created = discarded = 0

    for iv in interviews:
        existing = session.exec(select(NodeState).where(NodeState.id == iv.id)).first()
        if existing:
            log(f"  SKIP  NodeState {iv.id} ya existe")
            continue

        # D2: orphaned member
        if iv.member_id not in member_org_map:
            log(
                f"  DISCARD D2: interview {iv.id} "
                f"member_id={iv.member_id} no existe en members"
            )
            discarded += 1
            continue

        member_org = member_org_map[iv.member_id]
        if member_org not in org_to_campaign:
            log(
                f"  DISCARD D2 (no campaign): interview {iv.id} "
                f"org={member_org} no tiene campaign"
            )
            discarded += 1
            continue

        status = (
            NodeStateStatus.COMPLETED
            if iv.submitted_at is not None
            else NodeStateStatus.INVITED
        )

        session.add(NodeState(
            id=iv.id,
            node_id=iv.member_id,
            campaign_id=org_to_campaign[member_org],
            email_assigned=None,
            role_label=member_role_map.get(iv.member_id),
            context_notes=None,
            respondent_token=member_token_map.get(iv.member_id),
            status=status,
            invited_at=member_created_map.get(iv.member_id),
            completed_at=iv.submitted_at,
            created_at=NOW_UTC,
        ))
        log(f"  CREATE NodeState {iv.id} node={iv.member_id} status={status.value}")
        created += 1

    log(f"  → {created} creados, {discarded} descartados (D2).")
    return created, discarded


# ─── Validations ──────────────────────────────────────────────────────────────

def validate_migration(
    session: Session,
    before: dict[str, int],
    groups_total: int,
    members_total: int,
    members_discarded: int,
    interviews_total: int,
    interviews_discarded: int,
    org_ids: set[UUID],
    log: DualLog,
) -> tuple[bool, str]:
    """Run all 7 post-migration validation checks."""
    log("\n## PARTE 6 — Validaciones post-migración")
    conn = session.connection()
    all_ok = True
    first_failure = ""

    def chk(label: str, expected: int, actual: int) -> None:
        nonlocal all_ok, first_failure
        ok = expected == actual
        log(f"  {'✅' if ok else '❌'} {label}: expected={expected} actual={actual}")
        if not ok and all_ok:
            all_ok = False
            first_failure = f"{label}: esperado {expected}, obtenido {actual}"

    # (a) groups == nodes(unit)
    n_unit = conn.execute(
        text("SELECT COUNT(*) FROM nodes WHERE type='unit' AND deleted_at IS NULL")
    ).scalar_one()
    chk("(a) groups == nodes(unit)", groups_total, n_unit)

    # (b) members == nodes(person) + D3 discards
    n_person = conn.execute(
        text("SELECT COUNT(*) FROM nodes WHERE type='person' AND deleted_at IS NULL")
    ).scalar_one()
    chk("(b) members == nodes(person)+discarded_D3", members_total, n_person + members_discarded)

    # (c) interviews == node_states + D2 discards
    n_states = conn.execute(text("SELECT COUNT(*) FROM node_states")).scalar_one()
    chk("(c) interviews == node_states+discarded_D2", interviews_total, n_states + interviews_discarded)

    # (d) node_analyses FKs → no orphans in nodes
    orphans = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM node_analyses na
            LEFT JOIN nodes n ON n.id = na.group_id
            WHERE n.id IS NULL
        """)
    ).scalar_one()
    chk("(d) node_analyses.group_id FKs válidas (orphans==0)", 0, orphans)

    # (e) & (f) motor tables unchanged
    for table in MOTOR_TABLES:
        after = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
        chk(f"({'e' if table == 'analysis_runs' else 'f'}) {table} unchanged", before[table], after)

    # (g) each org has exactly 1 "Diagnóstico Inicial" campaign
    for org_id in sorted(org_ids, key=str):
        cnt = conn.execute(
            text("""
                SELECT COUNT(*) FROM assessment_campaigns
                WHERE organization_id = :oid AND name = 'Diagnóstico Inicial'
            """),
            {"oid": str(org_id)},
        ).scalar_one()
        chk(f"(g) org {org_id} tiene 1 campaign", 1, cnt)

    return all_ok, first_failure


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migra datos Group/Member/Interview al nuevo modelo Node/NodeState."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Ejecuta COMMIT real. Sin este flag hace ROLLBACK al final (dry-run).",
    )
    args = parser.parse_args()
    mode = "APPLY" if args.apply else "DRY-RUN"

    log = DualLog()
    log(f"[migrate] {mode} — {NOW_UTC.isoformat()}")
    log("=" * 64)

    with Session(engine) as session:
        # Snapshot motor counts BEFORE any changes
        before = snapshot_motor_counts(session)
        log("\n## SNAPSHOT MOTOR (antes)")
        for table, count in before.items():
            log(f"  {table}: {count}")

        # Pre-load all source data once (used by multiple parts)
        orgs = list(session.exec(select(Organization)).all())
        groups = list(session.exec(select(Group)).all())
        members = list(session.exec(select(Member)).all())
        interviews = list(session.exec(select(Interview)).all())

        org_ids: set[UUID] = {o.id for o in orgs}
        group_ids: set[UUID] = {g.id for g in groups}
        member_org_map: dict[UUID, UUID] = {m.id: m.organization_id for m in members}
        member_token_map: dict[UUID, str] = {m.id: m.interview_token for m in members}
        member_role_map: dict[UUID, str | None] = {m.id: m.role_label for m in members}
        member_created_map: dict[UUID, datetime] = {m.id: m.created_at for m in members}

        log(f"\n  Orgs: {len(orgs)} | Groups: {len(groups)} | "
            f"Members: {len(members)} | Interviews: {len(interviews)}")

        try:
            # Part 1 — AssessmentCampaigns
            org_to_campaign = migrate_campaigns(session, orgs, log)

            # Part 2 — Groups → Nodes(unit)
            root_units_by_org = migrate_groups_to_nodes(session, groups, log)

            # Part 3 — Members → Nodes(person)
            _, members_discarded = migrate_members_to_nodes(
                session, members, root_units_by_org, org_ids, group_ids, log
            )

            # Part 4 — Interviews → NodeStates
            _, interviews_discarded = migrate_interviews_to_node_states(
                session, interviews, org_to_campaign,
                member_org_map, member_token_map, member_role_map, member_created_map,
                log,
            )

            # Flush: make all inserts visible to validation queries (within transaction)
            session.flush()

            # Part 6 — Validations
            ok, failure_msg = validate_migration(
                session, before,
                groups_total=len(groups),
                members_total=len(members),
                members_discarded=members_discarded,
                interviews_total=len(interviews),
                interviews_discarded=interviews_discarded,
                org_ids=org_ids,
                log=log,
            )

            if not ok:
                session.rollback()
                log(f"\n❌ ROLLBACK: validación fallida — {failure_msg}")
                report_path = log.write_report(args.apply)
                log(f"\n[migrate] Reporte: {report_path}")
                return 1

            if args.apply:
                session.commit()
                log("\n✅ COMMIT: migración aplicada exitosamente.")
            else:
                session.rollback()
                log("\n⚠️  DRY-RUN: todas las validaciones pasaron. "
                    "Ejecutar con --apply para aplicar.")

        except RuntimeError as exc:
            session.rollback()
            log(f"\n❌ ABORT (caso no documentado): {exc}")
            report_path = log.write_report(args.apply)
            log(f"\n[migrate] Reporte: {report_path}")
            return 1
        except Exception:
            session.rollback()
            log("\n❌ ERROR inesperado. Transacción revertida.")
            raise

    log("\n## RESUMEN FINAL")
    log(f"  Modo: {mode} | Estado: OK")

    report_path = log.write_report(args.apply)
    log(f"  Reporte escrito en: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
