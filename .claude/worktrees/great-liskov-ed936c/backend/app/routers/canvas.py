"""Canvas-specific endpoints: templates and CSV import."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from app.core.dependencies import get_current_user
from app.db import get_session
from app.models.group import Group, GroupRead
from app.models.user import User, UserRole

router = APIRouter()


# ── Templates ──────────────────────────────────────────

TEMPLATES: dict[str, dict] = {
    "startup": {
        "name": "Startup (10-30 personas)",
        "description": "Estructura plana con áreas funcionales básicas",
        "nodes": [
            {"name": "CEO", "area": "Dirección", "level": 0, "children": [
                {"name": "CTO", "area": "Tecnología", "level": 1, "children": [
                    {"name": "Dev Lead", "area": "Tecnología", "level": 2},
                    {"name": "Diseñador", "area": "Tecnología", "level": 2},
                ]},
                {"name": "COO", "area": "Operaciones", "level": 1, "children": [
                    {"name": "Ops Manager", "area": "Operaciones", "level": 2},
                ]},
                {"name": "Head Comercial", "area": "Comercial", "level": 1, "children": [
                    {"name": "Ventas", "area": "Comercial", "level": 2},
                    {"name": "Marketing", "area": "Comercial", "level": 2},
                ]},
            ]},
        ],
    },
    "ong": {
        "name": "ONG pequeña",
        "description": "Organización con dirección, programas y operaciones",
        "nodes": [
            {"name": "Director(a) Ejecutivo(a)", "area": "Dirección", "level": 0, "children": [
                {"name": "Coordinador(a) de Programas", "area": "Programas", "level": 1, "children": [
                    {"name": "Programa A", "area": "Programas", "level": 2},
                    {"name": "Programa B", "area": "Programas", "level": 2},
                ]},
                {"name": "Administración y Finanzas", "area": "Admin", "level": 1},
                {"name": "Comunicaciones", "area": "Comunicaciones", "level": 1},
            ]},
        ],
    },
    "empresa_departamentos": {
        "name": "Empresa por departamentos",
        "description": "Estructura jerárquica tradicional con departamentos",
        "nodes": [
            {"name": "Gerente General", "area": "Dirección", "level": 0, "children": [
                {"name": "Dir. Financiero", "area": "Finanzas", "level": 1, "children": [
                    {"name": "Contabilidad", "area": "Finanzas", "level": 2},
                    {"name": "Tesorería", "area": "Finanzas", "level": 2},
                ]},
                {"name": "Dir. Comercial", "area": "Comercial", "level": 1, "children": [
                    {"name": "Ventas", "area": "Comercial", "level": 2},
                    {"name": "Marketing", "area": "Comercial", "level": 2},
                ]},
                {"name": "Dir. Operaciones", "area": "Operaciones", "level": 1, "children": [
                    {"name": "Producción", "area": "Operaciones", "level": 2},
                    {"name": "Logística", "area": "Operaciones", "level": 2},
                ]},
                {"name": "Dir. Talento Humano", "area": "RRHH", "level": 1},
            ]},
        ],
    },
    "equipo_proyecto": {
        "name": "Equipo de proyecto",
        "description": "Estructura para un equipo de proyecto específico",
        "nodes": [
            {"name": "Líder de Proyecto", "area": "Proyecto", "level": 0, "children": [
                {"name": "Analista", "area": "Proyecto", "level": 1},
                {"name": "Desarrollador", "area": "Proyecto", "level": 1},
                {"name": "QA", "area": "Proyecto", "level": 1},
                {"name": "Diseñador", "area": "Proyecto", "level": 1},
            ]},
        ],
    },
}


@router.get("/organizations/{org_id}/canvas/templates")
def list_templates(
    org_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    return [
        {"id": tid, "name": t["name"], "description": t["description"]}
        for tid, t in TEMPLATES.items()
    ]


@router.post("/organizations/{org_id}/canvas/templates/{template_id}")
def apply_template(
    org_id: UUID,
    template_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> dict:
    if current_user.role != UserRole.SUPERADMIN and current_user.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    template = TEMPLATES.get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    created: list[GroupRead] = []
    x_spacing = 250
    y_spacing = 150

    def create_nodes(
        nodes: list[dict],
        parent_id: UUID | None,
        depth: int,
        x_offset: float,
    ) -> float:
        x = x_offset
        for node_def in nodes:
            group = Group(
                organization_id=org_id,
                name=node_def["name"],
                area=node_def.get("area", ""),
                nivel_jerarquico=node_def.get("level"),
                parent_group_id=parent_id,
                position_x=x,
                position_y=depth * y_spacing,
            )
            session.add(group)
            session.flush()
            created.append(GroupRead.model_validate(group))

            children = node_def.get("children", [])
            if children:
                x = create_nodes(children, group.id, depth + 1, x)
            else:
                x += x_spacing

        return x

    create_nodes(template["nodes"], None, 0, 0)
    session.commit()

    return {"created": len(created), "nodes": [g.model_dump() for g in created]}


# ── CSV Import ─────────────────────────────────────────

class CsvRow(BaseModel):
    name: str
    role: str = ""
    area: str = ""
    boss: str = ""


class CsvImportRequest(BaseModel):
    rows: list[CsvRow]


@router.post("/organizations/{org_id}/canvas/import-csv")
def import_csv(
    org_id: UUID,
    payload: CsvImportRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> dict:
    if current_user.role != UserRole.SUPERADMIN and current_user.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if not payload.rows:
        raise HTTPException(status_code=400, detail="No data to import")

    # First pass: create all nodes keyed by name
    nodes_by_name: dict[str, Group] = {}
    y_spacing = 150
    x_spacing = 250

    # Find roots (no boss or boss not in list)
    names = {r.name for r in payload.rows}
    roots = [r for r in payload.rows if not r.boss or r.boss not in names]
    non_roots = [r for r in payload.rows if r.boss and r.boss in names]

    # Create root nodes
    x = 0.0
    for row in roots:
        group = Group(
            organization_id=org_id,
            name=row.name,
            tarea_general=row.role,
            area=row.area,
            position_x=x,
            position_y=0,
        )
        session.add(group)
        session.flush()
        nodes_by_name[row.name] = group
        x += x_spacing

    # Create child nodes (may need multiple passes for deep hierarchies)
    remaining = list(non_roots)
    max_iterations = 10
    for iteration in range(max_iterations):
        if not remaining:
            break
        still_remaining = []
        for row in remaining:
            parent = nodes_by_name.get(row.boss)
            if parent:
                # Calculate position based on parent
                siblings = [
                    g for g in nodes_by_name.values()
                    if g.parent_group_id == parent.id
                ]
                child_x = parent.position_x + len(siblings) * x_spacing
                child_y = parent.position_y + y_spacing

                group = Group(
                    organization_id=org_id,
                    name=row.name,
                    tarea_general=row.role,
                    area=row.area,
                    parent_group_id=parent.id,
                    position_x=child_x,
                    position_y=child_y,
                )
                session.add(group)
                session.flush()
                nodes_by_name[row.name] = group
            else:
                still_remaining.append(row)
        remaining = still_remaining

    # Any remaining rows with unresolved bosses: create as incomplete roots
    for row in remaining:
        group = Group(
            organization_id=org_id,
            name=row.name,
            tarea_general=row.role,
            area=row.area,
            position_x=x,
            position_y=0,
        )
        session.add(group)
        session.flush()
        nodes_by_name[row.name] = group
        x += x_spacing

    session.commit()

    return {
        "created": len(nodes_by_name),
        "unresolved_bosses": [r.name for r in remaining],
    }
