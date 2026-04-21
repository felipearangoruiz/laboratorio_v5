"""Migration dry-run — reporte READ-ONLY previo al Sprint 1.

Sprint 0, entregable final. Audita el estado actual de la base de datos
antes de migrar del modelo Group/Member/LateralRelation al nuevo modelo
Node/Edge/NodeState/AssessmentCampaign (ver docs/MODEL_PHILOSOPHY.md).

REGLA DE ORO: el script es READ-ONLY estricto. No emite INSERT, UPDATE,
DELETE ni DDL. Al final de la ejecución se hace `session.rollback()`
como seguro adicional aunque nunca se haya llamado a `session.commit()`.

Convención de ejecución (igual que init_db.sh / seed.py — desde /app
dentro del contenedor backend):

    docker compose exec backend uv run python scripts/migration_dry_run.py

El script produce dos salidas idénticas en contenido:
    1. stdout (útil para pipe o para revisar en vivo).
    2. scripts/migration_dry_run_report.md dentro del contenedor
       (mapeado a backend/scripts/migration_dry_run_report.md en el
       host). Si el archivo ya existe, se crea uno con timestamp.

Ver docs/MODEL_PHILOSOPHY.md §8 para la lista de 12 invariantes que
aplican post-migración; este script audita los datos actuales para
detectar violaciones potenciales.
"""
from __future__ import annotations

import io
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

# Asegurar que /app (la raíz del backend donde vive el paquete `app`) está en
# sys.path. Sin esto, ejecutar `python scripts/migration_dry_run.py` falla con
# ModuleNotFoundError porque Python solo agrega /app/scripts a sys.path.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlalchemy import text  # noqa: E402  (import after sys.path mutation)
from sqlmodel import Session, select  # noqa: E402

from app.db import engine  # noqa: E402
from app.models.analysis import (  # noqa: E402
    AnalysisRun,
    DocumentExtraction,
    EvidenceLink,
    Finding,
    GroupAnalysis,
    NodeAnalysis,
    OrgAnalysis,
    Recommendation,
)
from app.models.document import Document  # noqa: E402
from app.models.group import Group  # noqa: E402
from app.models.interview import Interview  # noqa: E402
from app.models.lateral_relation import LateralRelation  # noqa: E402
from app.models.member import Member  # noqa: E402
from app.models.organization import Organization  # noqa: E402

# Tipos válidos en el enum cerrado del nuevo modelo (decisión A3)
VALID_EDGE_TYPES: set[str] = {"lateral", "process"}

# Nombres de las tablas que el Sprint 1 va a crear (no deben preexistir)
NEW_MODEL_TABLES: list[str] = [
    "nodes",
    "edges",
    "assessment_campaigns",
    "node_states",
]


class DualWriter:
    """Escribe simultáneamente a stdout y a un buffer interno.

    Motivación: el reporte markdown debe ser idéntico al output de
    stdout. DualWriter evita que tengamos que repetir cada print.
    """

    def __init__(self) -> None:
        self.buffer = io.StringIO()

    def write(self, s: str = "") -> None:
        print(s)
        self.buffer.write(s + "\n")

    def getvalue(self) -> str:
        return self.buffer.getvalue()


def section(w: DualWriter, title: str, level: int = 2) -> None:
    w.write("")
    w.write(f"{'#' * level} {title}")
    w.write("")


def kv(w: DualWriter, label: str, value: Any) -> None:
    w.write(f"- **{label}**: {value}")


def block_1_old_model_counts(w: DualWriter, session: Session) -> None:
    section(w, "BLOQUE 1 — Counts del modelo viejo")

    orgs = session.exec(select(Organization)).all()
    groups = session.exec(select(Group)).all()
    members = session.exec(select(Member)).all()
    interviews = session.exec(select(Interview)).all()
    docs = session.exec(select(Document)).all()

    kv(w, "Organizations", len(orgs))
    kv(w, "Groups (totales)", len(groups))
    kv(w, "Members (totales)", len(members))
    kv(w, "Interviews (totales)", len(interviews))
    kv(w, "Documents (totales)", len(docs))

    # Por organización
    if orgs:
        w.write("")
        w.write("### Por organización")
        w.write("")
        w.write("| Organization | Groups | Members | Interviews |")
        w.write("|---|---:|---:|---:|")
        for org in orgs:
            g = sum(1 for x in groups if x.organization_id == org.id)
            m = sum(1 for x in members if x.organization_id == org.id)
            i = sum(1 for x in interviews if x.organization_id == org.id)
            # Escapar pipes en nombres para no romper el markdown
            name = (org.name or "(sin nombre)").replace("|", "\\|")
            w.write(f"| {name} (`{org.id}`) | {g} | {m} | {i} |")

    # Interviews por estado de miembro
    if members:
        w.write("")
        w.write("### Interviews por token_status del Member")
        w.write("")
        by_status: dict[str, int] = {}
        member_by_id = {m.id: m for m in members}
        for iv in interviews:
            m = member_by_id.get(iv.member_id)
            status = m.token_status.value if m and m.token_status else "(huérfana)"
            by_status[status] = by_status.get(status, 0) + 1
        for status, count in sorted(by_status.items()):
            kv(w, status, count)


def block_2_engine_counts(w: DualWriter, session: Session) -> None:
    section(w, "BLOQUE 2 — Counts del motor de análisis (informativo)")

    runs = session.exec(select(AnalysisRun)).all()
    node_analyses = session.exec(select(NodeAnalysis)).all()
    group_analyses = session.exec(select(GroupAnalysis)).all()
    org_analyses = session.exec(select(OrgAnalysis)).all()
    findings = session.exec(select(Finding)).all()
    recommendations = session.exec(select(Recommendation)).all()
    evidence_links = session.exec(select(EvidenceLink)).all()
    doc_extractions = session.exec(select(DocumentExtraction)).all()

    kv(w, "AnalysisRuns (totales)", len(runs))
    if runs:
        by_status: dict[str, int] = {}
        for r in runs:
            by_status[r.status] = by_status.get(r.status, 0) + 1
        w.write("")
        w.write("### AnalysisRuns por status")
        w.write("")
        for status, count in sorted(by_status.items()):
            kv(w, status, count)

    w.write("")
    kv(w, "NodeAnalyses", len(node_analyses))
    kv(w, "GroupAnalyses", len(group_analyses))
    kv(w, "OrgAnalyses", len(org_analyses))
    kv(w, "Findings", len(findings))
    kv(w, "Recommendations", len(recommendations))
    kv(w, "EvidenceLinks", len(evidence_links))
    kv(w, "DocumentExtractions", len(doc_extractions))


def block_3_edge_cases(w: DualWriter, session: Session) -> dict[str, int]:
    """Casos edge del modelo viejo. Devuelve dict de counts para resumen."""
    section(w, "BLOQUE 3 — Casos edge a resolver")

    counts: dict[str, int] = {}

    orgs = session.exec(select(Organization)).all()
    org_ids = {o.id for o in orgs}
    groups = session.exec(select(Group)).all()
    group_ids = {g.id for g in groups}
    members = session.exec(select(Member)).all()
    member_ids = {m.id for m in members}
    interviews = session.exec(select(Interview)).all()

    # 3.1 — Members con group_id null
    section(w, "3.1 Members con `group_id` NULL", level=3)
    orphans_3_1 = [m for m in members if m.group_id is None]
    counts["3.1_members_sin_grupo"] = len(orphans_3_1)
    if orphans_3_1:
        w.write(f"Total: **{len(orphans_3_1)}**. Cada uno requiere decisión manual.")
        w.write("")
        w.write("| id | organization_id | name | role_label | token_status | created_at |")
        w.write("|---|---|---|---|---|---|")
        for m in orphans_3_1:
            w.write(
                f"| `{m.id}` | `{m.organization_id}` | {m.name} | "
                f"{m.role_label or '(vacío)'} | {m.token_status.value} | "
                f"{m.created_at.isoformat()} |"
            )
    else:
        w.write("Ninguno. ✅")

    # 3.2 — Interviews huérfanas (member_id → Member inexistente)
    section(w, "3.2 Interviews huérfanas (member_id inexistente)", level=3)
    orphans_3_2 = [iv for iv in interviews if iv.member_id not in member_ids]
    counts["3.2_interviews_huerfanas"] = len(orphans_3_2)
    if orphans_3_2:
        w.write(f"Total: **{len(orphans_3_2)}**.")
        w.write("")
        w.write("| interview_id | member_id (fantasma) | organization_id | submitted_at |")
        w.write("|---|---|---|---|")
        for iv in orphans_3_2:
            submitted = iv.submitted_at.isoformat() if iv.submitted_at else "(no enviada)"
            w.write(f"| `{iv.id}` | `{iv.member_id}` | `{iv.organization_id}` | {submitted} |")
    else:
        w.write("Ninguna. ✅")

    # 3.3 — Members huérfanos (organization_id o group_id inexistente)
    section(w, "3.3 Members huérfanos (FK organization_id o group_id inexistente)", level=3)
    orphans_3_3_org = [m for m in members if m.organization_id not in org_ids]
    orphans_3_3_group = [
        m for m in members if m.group_id is not None and m.group_id not in group_ids
    ]
    counts["3.3_members_org_huerfano"] = len(orphans_3_3_org)
    counts["3.3_members_group_huerfano"] = len(orphans_3_3_group)
    if orphans_3_3_org or orphans_3_3_group:
        if orphans_3_3_org:
            w.write(f"**Members con organization_id inexistente: {len(orphans_3_3_org)}**")
            w.write("")
            w.write("| id | name | organization_id (fantasma) |")
            w.write("|---|---|---|")
            for m in orphans_3_3_org:
                w.write(f"| `{m.id}` | {m.name} | `{m.organization_id}` |")
            w.write("")
        if orphans_3_3_group:
            w.write(f"**Members con group_id inexistente: {len(orphans_3_3_group)}**")
            w.write("")
            w.write("| id | name | organization_id | group_id (fantasma) |")
            w.write("|---|---|---|---|")
            for m in orphans_3_3_group:
                w.write(
                    f"| `{m.id}` | {m.name} | `{m.organization_id}` | `{m.group_id}` |"
                )
    else:
        w.write("Ninguno. ✅")

    # 3.4 — Groups sin Members
    section(w, "3.4 Groups sin Members asociados", level=3)
    members_by_group: dict[UUID, int] = {}
    for m in members:
        if m.group_id is not None:
            members_by_group[m.group_id] = members_by_group.get(m.group_id, 0) + 1
    empty_groups = [g for g in groups if members_by_group.get(g.id, 0) == 0]
    counts["3.4_groups_vacios"] = len(empty_groups)
    if empty_groups:
        w.write(
            f"Total: **{len(empty_groups)}**. Un unit sin miembros no es inválido, "
            "pero vale la pena verificar que no son groups olvidados."
        )
        w.write("")
        w.write("| id | name | node_type | organization_id | is_default |")
        w.write("|---|---|---|---|---|")
        for g in empty_groups:
            w.write(
                f"| `{g.id}` | {g.name} | {g.node_type} | "
                f"`{g.organization_id}` | {g.is_default} |"
            )
    else:
        w.write("Ninguno. ✅")

    # 3.5 — Members sin Interview
    section(w, "3.5 Members sin Interview asociada", level=3)
    members_with_interview = {iv.member_id for iv in interviews}
    members_no_interview = [m for m in members if m.id not in members_with_interview]
    counts["3.5_members_sin_interview"] = len(members_no_interview)
    w.write(
        f"Total: **{len(members_no_interview)}** de {len(members)} members "
        "nunca tuvieron entrevista."
    )
    if members_no_interview:
        w.write("")
        w.write("| id | name | token_status | organization_id |")
        w.write("|---|---|---|---|")
        for m in members_no_interview:
            w.write(
                f"| `{m.id}` | {m.name} | {m.token_status.value} | "
                f"`{m.organization_id}` |"
            )

    # 3.6 — Groups con position NULL o (0, 0)
    section(w, "3.6 Groups con position_x / position_y NULL o (0, 0)", level=3)
    # position_x y position_y son floats NOT NULL con default 0.0 (ver group.py)
    # así que NULL es imposible; revisamos solo (0, 0).
    zero_pos = [g for g in groups if g.position_x == 0.0 and g.position_y == 0.0]
    counts["3.6_groups_posicion_cero"] = len(zero_pos)
    w.write(
        f"Total con posición (0, 0): **{len(zero_pos)}** de {len(groups)} groups. "
        "Nota: position_x/y son floats NOT NULL con default 0.0, NULL no es posible; "
        "(0, 0) puede ser legítimo (nodo en el origen del canvas) o por default sin "
        "arrastre. La migración debería asignar posiciones por defecto en grilla."
    )
    if zero_pos and len(zero_pos) <= 20:
        w.write("")
        w.write("| id | name | node_type | organization_id |")
        w.write("|---|---|---|---|")
        for g in zero_pos:
            w.write(
                f"| `{g.id}` | {g.name} | {g.node_type} | `{g.organization_id}` |"
            )
    elif len(zero_pos) > 20:
        w.write(f"(demasiados para listar — {len(zero_pos)} items; ver logs de SQL si necesitás detalle)")

    # 3.7 — Otras inconsistencias de referential integrity
    section(w, "3.7 Otras inconsistencias de referential integrity", level=3)
    other_issues: list[str] = []
    # Interviews con organization_id inexistente
    for iv in interviews:
        if iv.organization_id not in org_ids:
            other_issues.append(
                f"Interview `{iv.id}` tiene organization_id `{iv.organization_id}` "
                "inexistente."
            )
    # Interviews con group_id no-NULL pero inexistente
    for iv in interviews:
        if iv.group_id is not None and iv.group_id not in group_ids:
            other_issues.append(
                f"Interview `{iv.id}` tiene group_id `{iv.group_id}` inexistente."
            )
    # Groups con parent_group_id inexistente
    for g in groups:
        if g.parent_group_id is not None and g.parent_group_id not in group_ids:
            other_issues.append(
                f"Group `{g.id}` ({g.name}) tiene parent_group_id "
                f"`{g.parent_group_id}` inexistente."
            )
    # Groups con organization_id inexistente
    for g in groups:
        if g.organization_id not in org_ids:
            other_issues.append(
                f"Group `{g.id}` ({g.name}) tiene organization_id "
                f"`{g.organization_id}` inexistente."
            )
    # Documents con organization_id inexistente
    docs = session.exec(select(Document)).all()
    for d in docs:
        if d.organization_id not in org_ids:
            other_issues.append(
                f"Document `{d.id}` ({d.label}) tiene organization_id "
                f"`{d.organization_id}` inexistente."
            )

    counts["3.7_otras_inconsistencias"] = len(other_issues)
    if other_issues:
        w.write(f"Total: **{len(other_issues)}**.")
        w.write("")
        for issue in other_issues:
            w.write(f"- {issue}")
    else:
        w.write("Ninguna. ✅")

    # 3.8 — Colisión con tablas del nuevo modelo
    section(w, "3.8 Colisión con tablas del nuevo modelo", level=3)
    existing_new_tables: list[tuple[str, int]] = []
    # Usamos session.connection().execute() para obtener Result con scalar()
    # en lugar de session.exec(), que devuelve Row objects ambiguos.
    conn = session.connection()
    for tname in NEW_MODEL_TABLES:
        exists_count = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = :tname"
            ),
            {"tname": tname},
        ).scalar_one()
        if int(exists_count) > 0:
            row_count = conn.execute(text(f'SELECT COUNT(*) FROM "{tname}"')).scalar_one()
            existing_new_tables.append((tname, int(row_count)))

    counts["3.8_tablas_colisionadas"] = len(existing_new_tables)
    if existing_new_tables:
        w.write(
            f"⚠️ **{len(existing_new_tables)} tabla(s) del nuevo modelo ya existen** "
            "en la base. Esto rompería la migración Alembic con autogenerate si no "
            "se resuelve antes del Sprint 1."
        )
        w.write("")
        w.write("| Tabla | Rows |")
        w.write("|---|---:|")
        for tname, rc in existing_new_tables:
            w.write(f"| `{tname}` | {rc} |")
    else:
        w.write(
            "Ninguna de las tablas nuevas (`nodes`, `edges`, `assessment_campaigns`, "
            "`node_states`) existe todavía. ✅ Sprint 1 puede asumir base limpia."
        )

    return counts


def block_4_engine_integrity(w: DualWriter, session: Session) -> dict[str, int]:
    """Integridad referencial del motor. Devuelve counts para resumen."""
    section(w, "BLOQUE 4 — Análisis de impacto sobre el motor de análisis")

    counts: dict[str, int] = {}

    orgs = session.exec(select(Organization)).all()
    org_ids = {o.id for o in orgs}
    groups = session.exec(select(Group)).all()
    group_ids = {g.id for g in groups}
    docs = session.exec(select(Document)).all()
    doc_ids = {d.id for d in docs}

    node_analyses = session.exec(select(NodeAnalysis)).all()
    group_analyses = session.exec(select(GroupAnalysis)).all()
    org_analyses = session.exec(select(OrgAnalysis)).all()
    findings = session.exec(select(Finding)).all()
    recommendations = session.exec(select(Recommendation)).all()
    evidence_links = session.exec(select(EvidenceLink)).all()
    doc_extractions = session.exec(select(DocumentExtraction)).all()

    na_ids = {na.id for na in node_analyses}
    ga_ids = {ga.id for ga in group_analyses}

    # 4.1 NodeAnalysis.group_id → groups
    section(w, "4.1 NodeAnalysis con group_id huérfano", level=3)
    orph_4_1 = [na for na in node_analyses if na.group_id not in group_ids]
    counts["4.1_node_analyses_huerfanos"] = len(orph_4_1)
    if orph_4_1:
        w.write(f"Total: **{len(orph_4_1)}**.")
        for na in orph_4_1:
            w.write(f"- NodeAnalysis `{na.id}` → group_id `{na.group_id}` (inexistente)")
    else:
        w.write("Ninguno. ✅")

    # 4.2 GroupAnalysis.group_id → groups
    section(w, "4.2 GroupAnalysis con group_id huérfano", level=3)
    orph_4_2 = [ga for ga in group_analyses if ga.group_id not in group_ids]
    counts["4.2_group_analyses_huerfanos"] = len(orph_4_2)
    if orph_4_2:
        w.write(f"Total: **{len(orph_4_2)}**.")
        for ga in orph_4_2:
            w.write(f"- GroupAnalysis `{ga.id}` → group_id `{ga.group_id}` (inexistente)")
    else:
        w.write("Ninguno. ✅")

    # 4.3 OrgAnalysis.org_id → organizations
    section(w, "4.3 OrgAnalysis con org_id huérfano", level=3)
    orph_4_3 = [oa for oa in org_analyses if oa.org_id not in org_ids]
    counts["4.3_org_analyses_huerfanos"] = len(orph_4_3)
    if orph_4_3:
        w.write(f"Total: **{len(orph_4_3)}**.")
        for oa in orph_4_3:
            w.write(f"- OrgAnalysis `{oa.id}` → org_id `{oa.org_id}` (inexistente)")
    else:
        w.write("Ninguno. ✅")

    # 4.4 Findings.node_ids JSONB con UUIDs huérfanos
    section(w, "4.4 Findings con node_ids huérfanos", level=3)
    finding_issues: list[tuple[UUID, list[str]]] = []
    for f in findings:
        bad: list[str] = []
        for nid in f.node_ids or []:
            try:
                uid = UUID(str(nid))
            except (ValueError, TypeError):
                bad.append(f"{nid!r} (no es UUID válido)")
                continue
            if uid not in group_ids:
                bad.append(str(uid))
        if bad:
            finding_issues.append((f.id, bad))
    counts["4.4_findings_node_ids_huerfanos"] = len(finding_issues)
    if finding_issues:
        w.write(f"Total de findings con node_ids huérfanos: **{len(finding_issues)}**.")
        for fid, bad in finding_issues:
            w.write(f"- Finding `{fid}` → node_ids huérfanos: {bad}")
    else:
        w.write("Ninguno. ✅")

    # 4.5 EvidenceLinks → NodeAnalysis / GroupAnalysis
    section(w, "4.5 EvidenceLinks con FK huérfano", level=3)
    el_issues: list[str] = []
    for el in evidence_links:
        if el.node_analysis_id is not None and el.node_analysis_id not in na_ids:
            el_issues.append(
                f"EvidenceLink `{el.id}` → node_analysis_id "
                f"`{el.node_analysis_id}` (inexistente)"
            )
        if el.group_analysis_id is not None and el.group_analysis_id not in ga_ids:
            el_issues.append(
                f"EvidenceLink `{el.id}` → group_analysis_id "
                f"`{el.group_analysis_id}` (inexistente)"
            )
    counts["4.5_evidence_links_huerfanos"] = len(el_issues)
    if el_issues:
        w.write(f"Total: **{len(el_issues)}**.")
        for issue in el_issues:
            w.write(f"- {issue}")
    else:
        w.write("Ninguno. ✅")

    # 4.6 Recommendations.node_ids JSONB huérfanos
    section(w, "4.6 Recommendations con node_ids huérfanos", level=3)
    rec_issues: list[tuple[UUID, list[str]]] = []
    for r in recommendations:
        bad = []
        for nid in r.node_ids or []:
            try:
                uid = UUID(str(nid))
            except (ValueError, TypeError):
                bad.append(f"{nid!r} (no es UUID válido)")
                continue
            if uid not in group_ids:
                bad.append(str(uid))
        if bad:
            rec_issues.append((r.id, bad))
    counts["4.6_recommendations_node_ids_huerfanos"] = len(rec_issues)
    if rec_issues:
        w.write(f"Total: **{len(rec_issues)}**.")
        for rid, bad in rec_issues:
            w.write(f"- Recommendation `{rid}` → node_ids huérfanos: {bad}")
    else:
        w.write("Ninguno. ✅")

    # 4.7 DocumentExtractions → documents + organizations
    section(w, "4.7 DocumentExtractions con FK huérfano", level=3)
    de_issues: list[str] = []
    for de in doc_extractions:
        if de.doc_id not in doc_ids:
            de_issues.append(
                f"DocumentExtraction `{de.id}` → doc_id `{de.doc_id}` (inexistente)"
            )
        if de.org_id not in org_ids:
            de_issues.append(
                f"DocumentExtraction `{de.id}` → org_id `{de.org_id}` (inexistente)"
            )
    counts["4.7_document_extractions_huerfanas"] = len(de_issues)
    if de_issues:
        w.write(f"Total: **{len(de_issues)}**.")
        for issue in de_issues:
            w.write(f"- {issue}")
    else:
        w.write("Ninguno. ✅")

    total_engine_issues = sum(counts.values())
    section(w, "Resumen Bloque 4", level=3)
    kv(w, "Total inconsistencias del motor", total_engine_issues)
    counts["_total"] = total_engine_issues
    return counts


def block_5_invariants_simulation(w: DualWriter, session: Session) -> dict[str, int]:
    """Simular invariantes del nuevo modelo sobre datos actuales."""
    section(w, "BLOQUE 5 — Validación de invariantes del nuevo modelo")

    counts: dict[str, int] = {}
    groups = session.exec(select(Group)).all()
    members = session.exec(select(Member)).all()
    member_ids = {m.id for m in members}
    group_ids = {g.id for g in groups}

    # 5.1 — Ningún Group con parent_group_id apuntando a un Member
    section(
        w,
        "5.1 ¿Algún Group tiene parent_group_id apuntando a un Member?",
        level=3,
    )
    # parent_group_id es FK a groups.id, así que estructuralmente no debería ocurrir.
    # Pero chequeamos por si algún registro tiene un UUID que coincide con un Member.
    violators_5_1 = [g for g in groups if g.parent_group_id in member_ids]
    counts["5.1_group_parent_es_member"] = len(violators_5_1)
    if violators_5_1:
        w.write(f"⚠️ **{len(violators_5_1)}** violaciones:")
        for g in violators_5_1:
            w.write(f"- Group `{g.id}` ({g.name}) parent_group_id `{g.parent_group_id}` es un Member.")
    else:
        w.write("Ninguno. ✅ La FK `parent_group_id → groups.id` lo impide estructuralmente.")

    # 5.2 — Jerarquía implícita inválida de Members
    # Un Member solo referencia organization_id + group_id. No hay jerarquía
    # member→member en el modelo actual. La invariante "person requiere parent
    # unit" se traduce post-migración a "member debe tener group_id no null",
    # que ya cubrimos en 3.1. Esto es informativo.
    section(w, "5.2 Jerarquía implícita inválida de Members", level=3)
    w.write(
        "En el modelo actual no existe jerarquía member→member (no hay "
        "`parent_member_id`). La invariante del nuevo modelo *\"todo person debe "
        "tener parent_node_id no NULL apuntando a un unit\"* se traduce "
        "post-migración a *\"todo Member debe tener group_id no NULL\"*, ya "
        "cubierto en 3.1."
    )
    counts["5.2_miembros_jerarquia_invalida"] = counts.get("5.2_miembros_jerarquia_invalida", 0)

    # 5.3 — LateralRelations con tipo fuera del enum cerrado
    section(w, "5.3 LateralRelations con tipo fuera del enum {lateral, process}", level=3)
    laterals = session.exec(select(LateralRelation)).all()
    out_of_enum = [lr for lr in laterals if lr.type not in VALID_EDGE_TYPES]
    counts["5.3_lateral_fuera_enum"] = len(out_of_enum)
    counts["5.3_lateral_total"] = len(laterals)
    w.write(f"Total LateralRelations existentes: **{len(laterals)}**.")
    w.write(f"LateralRelations con tipo NO mapeable a (lateral, process): **{len(out_of_enum)}**.")
    if out_of_enum:
        w.write("")
        w.write(
            "Cada una requiere reasignación manual antes de Sprint 1 — si no, la "
            "migración las pierde o las deja en estado inválido."
        )
        w.write("")
        w.write("| id | type actual | source_node_id | target_node_id | organization_id |")
        w.write("|---|---|---|---|---|")
        for lr in out_of_enum:
            w.write(
                f"| `{lr.id}` | **{lr.type}** | `{lr.source_node_id}` | "
                f"`{lr.target_node_id}` | `{lr.organization_id}` |"
            )

    # Adicional: laterals con source/target huérfanos
    lat_orphans = [
        lr
        for lr in laterals
        if lr.source_node_id not in group_ids or lr.target_node_id not in group_ids
    ]
    counts["5.3_lateral_nodos_huerfanos"] = len(lat_orphans)
    if lat_orphans:
        w.write("")
        w.write(f"⚠️ LateralRelations con source/target apuntando a Groups inexistentes: **{len(lat_orphans)}**.")
        for lr in lat_orphans:
            w.write(f"- LateralRelation `{lr.id}` ({lr.type})")

    return counts


def section_decisions(
    w: DualWriter,
    edge_counts: dict[str, int],
    engine_counts: dict[str, int],
    inv_counts: dict[str, int],
) -> None:
    """Sección final con placeholders para que el equipo escriba decisiones."""
    section(w, "DECISIONES REQUERIDAS ANTES DEL SPRINT 1", level=1)

    w.write(
        "Esta sección debe llenarse a mano por el equipo antes de ejecutar la "
        "migración real. Cada decisión se commitea junto con el script para dejar "
        "el contrato de entrada versionado."
    )

    # D1 — Members con group_id NULL
    section(w, "D1 — Members con group_id NULL", level=2)
    n = edge_counts.get("3.1_members_sin_grupo", 0)
    w.write(f"Casos encontrados: **{n}**.")
    w.write("")
    w.write("Opciones:")
    w.write("- (a) Crear una regla heurística global: asignar todos a un unit por defecto (ej: un unit \"Sin área\" creado en la migración).")
    w.write("- (b) Decidir caso por caso usando la tabla 3.1.")
    w.write("- (c) Dejar como `parent_node_id` NULL (viola invariante §8.3 — requiere enmienda a la invariante si se elige).")
    w.write("")
    w.write("**Decisión del equipo:** _[pendiente — escribir aquí]_")

    # D2 — Interviews huérfanas
    section(w, "D2 — Interviews huérfanas (3.2)", level=2)
    n = edge_counts.get("3.2_interviews_huerfanas", 0)
    w.write(f"Casos encontrados: **{n}**.")
    w.write("")
    w.write("Opciones: (a) descartar; (b) reasignar a un Member stub nuevo.")
    w.write("")
    w.write("**Decisión del equipo:** _[pendiente]_")

    # D3 — Members huérfanos
    section(w, "D3 — Members huérfanos (3.3)", level=2)
    no = edge_counts.get("3.3_members_org_huerfano", 0)
    ng = edge_counts.get("3.3_members_group_huerfano", 0)
    w.write(f"Organization huérfano: **{no}**. Group huérfano: **{ng}**.")
    w.write("")
    w.write("Opciones: (a) descartar; (b) reasignar organization; (c) reasignar group.")
    w.write("")
    w.write("**Decisión del equipo:** _[pendiente]_")

    # D4 — LateralRelations con tipo fuera del enum
    section(w, "D4 — LateralRelations con tipo fuera de {lateral, process} (5.3)", level=2)
    n = inv_counts.get("5.3_lateral_fuera_enum", 0)
    t = inv_counts.get("5.3_lateral_total", 0)
    w.write(f"Casos: **{n}** de {t} totales.")
    w.write("")
    w.write(
        "Para cada registro listado en §5.3 hay que elegir `lateral` o `process`. "
        "Criterio sugerido: `colaboracion` / `coordinacion` / `comunicacion` → "
        "`lateral`; `dependencia` / `flujo` / `handoff` / `supervision` → "
        "`process`. El valor `otro` no tiene mapeo automático: decisión explícita."
    )
    w.write("")
    w.write("**Decisión del equipo:** _[pendiente — mapeo por registro o regla heurística]_")

    # D5 — Colisión de tablas nuevas
    section(w, "D5 — Colisión con tablas del nuevo modelo (3.8)", level=2)
    n = edge_counts.get("3.8_tablas_colisionadas", 0)
    w.write(f"Tablas ya existentes: **{n}**.")
    w.write("")
    w.write("Opciones: truncar; renombrar (`_legacy`); abortar Sprint 1 hasta entender origen.")
    w.write("")
    w.write("**Decisión del equipo:** _[pendiente]_")

    # D6 — Inconsistencias del motor
    section(w, "D6 — Inconsistencias preexistentes del motor (Bloque 4)", level=2)
    n = engine_counts.get("_total", 0)
    w.write(f"Inconsistencias totales: **{n}**.")
    if n <= 5:
        w.write(
            "Heurística: **arreglar antes de Sprint 1** (≤5 casos, es costo-efectivo "
            "resolverlos ahora)."
        )
    else:
        w.write(
            "Heurística: **ticket separado** (>5 casos, mejor no bloquear el Sprint "
            "1 — la migración preserva UUIDs, así que el problema no empeora)."
        )
    w.write("")
    w.write("**Decisión del equipo:** _[pendiente]_")

    # D7 — Groups sin members / posición (0, 0)
    section(w, "D7 — Nodos sin members y posiciones en el origen", level=2)
    empty = edge_counts.get("3.4_groups_vacios", 0)
    zero = edge_counts.get("3.6_groups_posicion_cero", 0)
    w.write(f"Groups sin members: **{empty}**. Groups con posición (0, 0): **{zero}**.")
    w.write("")
    w.write(
        "Opciones: (a) asignar posiciones auto en grilla durante migración; (b) "
        "dejar como están y que el admin los reacomode en el canvas."
    )
    w.write("")
    w.write("**Decisión del equipo:** _[pendiente]_")


def executive_summary(
    w: DualWriter,
    edge_counts: dict[str, int],
    engine_counts: dict[str, int],
    inv_counts: dict[str, int],
) -> None:
    section(w, "Resumen ejecutivo", level=1)
    w.write("| Categoría | Count |")
    w.write("|---|---:|")
    w.write(f"| 3.1 Members sin grupo | {edge_counts.get('3.1_members_sin_grupo', 0)} |")
    w.write(f"| 3.2 Interviews huérfanas | {edge_counts.get('3.2_interviews_huerfanas', 0)} |")
    w.write(
        f"| 3.3 Members con org huérfano | "
        f"{edge_counts.get('3.3_members_org_huerfano', 0)} |"
    )
    w.write(
        f"| 3.3 Members con group huérfano | "
        f"{edge_counts.get('3.3_members_group_huerfano', 0)} |"
    )
    w.write(f"| 3.4 Groups sin members | {edge_counts.get('3.4_groups_vacios', 0)} |")
    w.write(f"| 3.5 Members sin interview | {edge_counts.get('3.5_members_sin_interview', 0)} |")
    w.write(
        f"| 3.6 Groups con posición (0, 0) | "
        f"{edge_counts.get('3.6_groups_posicion_cero', 0)} |"
    )
    w.write(f"| 3.7 Otras inconsistencias FK | {edge_counts.get('3.7_otras_inconsistencias', 0)} |")
    w.write(f"| 3.8 Tablas del nuevo modelo ya existentes | {edge_counts.get('3.8_tablas_colisionadas', 0)} |")
    w.write(f"| **4.x Inconsistencias del motor (total)** | **{engine_counts.get('_total', 0)}** |")
    w.write(f"| 5.1 Group parent = Member | {inv_counts.get('5.1_group_parent_es_member', 0)} |")
    w.write(
        f"| 5.3 LateralRelations fuera del enum | "
        f"{inv_counts.get('5.3_lateral_fuera_enum', 0)} de "
        f"{inv_counts.get('5.3_lateral_total', 0)} |"
    )


def write_report_to_disk(report_md: str) -> Path:
    """Persiste el reporte. Si el archivo existe, usa sufijo timestamp."""
    scripts_dir = Path(__file__).parent
    target = scripts_dir / "migration_dry_run_report.md"
    if target.exists():
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        target = scripts_dir / f"migration_dry_run_report_{ts}.md"
    target.write_text(report_md, encoding="utf-8")
    return target


def main() -> int:
    w = DualWriter()

    ts = datetime.now(timezone.utc).isoformat()
    w.write("# Migration Dry-Run Report")
    w.write("")
    w.write(f"_Generado: **{ts}** (UTC)_")
    w.write("")
    w.write(
        "Reporte READ-ONLY previo al Sprint 1 del refactor Node + Edge. "
        "Ver `docs/MODEL_PHILOSOPHY.md` y `docs/DEUDA_DOCUMENTAL.md`."
    )

    # Sesión sin autoflush. Al final hacemos rollback explícito como seguro
    # adicional, aunque nunca emitamos nada de escritura.
    with Session(engine, autoflush=False, autocommit=False) as session:
        try:
            block_1_old_model_counts(w, session)
            block_2_engine_counts(w, session)
            edge_counts = block_3_edge_cases(w, session)
            engine_counts = block_4_engine_integrity(w, session)
            inv_counts = block_5_invariants_simulation(w, session)

            executive_summary(w, edge_counts, engine_counts, inv_counts)
            section_decisions(w, edge_counts, engine_counts, inv_counts)
        finally:
            # Seguro: aunque el script es READ-ONLY, forzamos rollback para
            # asegurar que ningún flush implícito termine persistiéndose.
            session.rollback()

    target = write_report_to_disk(w.getvalue())
    w.write("")
    w.write(f"_Reporte escrito a `{target.relative_to(Path(__file__).parent.parent)}`._")
    print(f"\n[dry-run] Reporte persistido en: {target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
