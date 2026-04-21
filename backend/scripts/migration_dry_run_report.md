# Migration Dry-Run Report

_Generado: **2026-04-21T16:06:32.193624+00:00** (UTC)_

Reporte READ-ONLY previo al Sprint 1 del refactor Node + Edge. Ver `docs/MODEL_PHILOSOPHY.md` y `docs/DEUDA_DOCUMENTAL.md`.

## BLOQUE 1 — Counts del modelo viejo

- **Organizations**: 4
- **Groups (totales)**: 20
- **Members (totales)**: 6
- **Interviews (totales)**: 6
- **Documents (totales)**: 0

### Por organización

| Organization | Groups | Members | Interviews |
|---|---:|---:|---:|
| Laboratorio Demo (`26a11ff1-14d5-44a8-83bd-ce2e26e49bd4`) | 1 | 0 | 0 |
| katronix (`598b3037-9241-4b99-9c35-2b3a13e523a5`) | 0 | 0 | 0 |
| ca (`5f9faec5-56c4-4550-84a3-b9c6d55388b5`) | 11 | 0 | 0 |
| Constructora Meridian SAS (`984bdeaf-14e8-47b9-b1e0-3c595b44bff8`) | 8 | 6 | 6 |

### Interviews por token_status del Member

- **completed**: 6

## BLOQUE 2 — Counts del motor de análisis (informativo)

- **AnalysisRuns (totales)**: 3

### AnalysisRuns por status

- **completed**: 1
- **running**: 2

- **NodeAnalyses**: 10
- **GroupAnalyses**: 3
- **OrgAnalyses**: 1
- **Findings**: 4
- **Recommendations**: 4
- **EvidenceLinks**: 0
- **DocumentExtractions**: 0

## BLOQUE 3 — Casos edge a resolver


### 3.1 Members con `group_id` NULL

Ninguno. ✅

### 3.2 Interviews huérfanas (member_id inexistente)

Ninguna. ✅

### 3.3 Members huérfanos (FK organization_id o group_id inexistente)

Ninguno. ✅

### 3.4 Groups sin Members asociados

Total: **14**. Un unit sin miembros no es inválido, pero vale la pena verificar que no son groups olvidados.

| id | name | node_type | organization_id | is_default |
|---|---|---|---|---|
| `ae41c538-38ca-4350-a58e-e131fff43bb4` | default | area | `26a11ff1-14d5-44a8-83bd-ce2e26e49bd4` | True |
| `706236b7-c0d7-4996-9a10-636414728918` | Gerente General | area | `5f9faec5-56c4-4550-84a3-b9c6d55388b5` | False |
| `d108b8b6-6dc6-4a5b-991f-c86b2e71c16b` | Dir. Financiero | area | `5f9faec5-56c4-4550-84a3-b9c6d55388b5` | False |
| `88d98167-6b4d-4f65-9194-f73dbbcda9bd` | Contabilidad | area | `5f9faec5-56c4-4550-84a3-b9c6d55388b5` | False |
| `0a05860b-433a-4911-bf96-4498c6a44f87` | Tesorería | area | `5f9faec5-56c4-4550-84a3-b9c6d55388b5` | False |
| `bfd0a363-1328-42b9-9c41-82f6a65a48e6` | Dir. Comercial | area | `5f9faec5-56c4-4550-84a3-b9c6d55388b5` | False |
| `4be36290-8f91-44e8-b506-06763bdca5bb` | Ventas | area | `5f9faec5-56c4-4550-84a3-b9c6d55388b5` | False |
| `8cef4216-c149-42cb-b3b7-dcb060c2223d` | Marketing | area | `5f9faec5-56c4-4550-84a3-b9c6d55388b5` | False |
| `5dfff697-00a7-47c7-b98c-d8b67b7429f6` | Dir. Operaciones | area | `5f9faec5-56c4-4550-84a3-b9c6d55388b5` | False |
| `23de9d91-f843-4c2c-a1d7-7cc169f7a643` | Producción | area | `5f9faec5-56c4-4550-84a3-b9c6d55388b5` | False |
| `0597d688-89d7-45be-8c74-d0c7e48a2e9d` | Logística | area | `5f9faec5-56c4-4550-84a3-b9c6d55388b5` | False |
| `9d02487e-4761-4516-be5b-f8eb811b73fe` | Dir. Talento Humano | area | `5f9faec5-56c4-4550-84a3-b9c6d55388b5` | False |
| `a0a2b445-4c5c-44f4-a517-c7f6780301fa` | Comercial | area | `984bdeaf-14e8-47b9-b1e0-3c595b44bff8` | False |
| `5150db27-477b-428d-862c-4e9388c51b80` | Operaciones | area | `984bdeaf-14e8-47b9-b1e0-3c595b44bff8` | False |

### 3.5 Members sin Interview asociada

Total: **0** de 6 members nunca tuvieron entrevista.

### 3.6 Groups con position_x / position_y NULL o (0, 0)

Total con posición (0, 0): **2** de 20 groups. Nota: position_x/y son floats NOT NULL con default 0.0, NULL no es posible; (0, 0) puede ser legítimo (nodo en el origen del canvas) o por default sin arrastre. La migración debería asignar posiciones por defecto en grilla.

| id | name | node_type | organization_id |
|---|---|---|---|
| `ae41c538-38ca-4350-a58e-e131fff43bb4` | default | area | `26a11ff1-14d5-44a8-83bd-ce2e26e49bd4` |
| `706236b7-c0d7-4996-9a10-636414728918` | Gerente General | area | `5f9faec5-56c4-4550-84a3-b9c6d55388b5` |

### 3.7 Otras inconsistencias de referential integrity

Ninguna. ✅

### 3.8 Colisión con tablas del nuevo modelo

Ninguna de las tablas nuevas (`nodes`, `edges`, `assessment_campaigns`, `node_states`) existe todavía. ✅ Sprint 1 puede asumir base limpia.

## BLOQUE 4 — Análisis de impacto sobre el motor de análisis


### 4.1 NodeAnalysis con group_id huérfano

Ninguno. ✅

### 4.2 GroupAnalysis con group_id huérfano

Ninguno. ✅

### 4.3 OrgAnalysis con org_id huérfano

Ninguno. ✅

### 4.4 Findings con node_ids huérfanos

Ninguno. ✅

### 4.5 EvidenceLinks con FK huérfano

Ninguno. ✅

### 4.6 Recommendations con node_ids huérfanos

Ninguno. ✅

### 4.7 DocumentExtractions con FK huérfano

Ninguno. ✅

### Resumen Bloque 4

- **Total inconsistencias del motor**: 0

## BLOQUE 5 — Validación de invariantes del nuevo modelo


### 5.1 ¿Algún Group tiene parent_group_id apuntando a un Member?

Ninguno. ✅ La FK `parent_group_id → groups.id` lo impide estructuralmente.

### 5.2 Jerarquía implícita inválida de Members

En el modelo actual no existe jerarquía member→member (no hay `parent_member_id`). La invariante del nuevo modelo *"todo person debe tener parent_node_id no NULL apuntando a un unit"* se traduce post-migración a *"todo Member debe tener group_id no NULL"*, ya cubierto en 3.1.

### 5.3 LateralRelations con tipo fuera del enum {lateral, process}

Total LateralRelations existentes: **0**.
LateralRelations con tipo NO mapeable a (lateral, process): **0**.

# Resumen ejecutivo

| Categoría | Count |
|---|---:|
| 3.1 Members sin grupo | 0 |
| 3.2 Interviews huérfanas | 0 |
| 3.3 Members con org huérfano | 0 |
| 3.3 Members con group huérfano | 0 |
| 3.4 Groups sin members | 14 |
| 3.5 Members sin interview | 0 |
| 3.6 Groups con posición (0, 0) | 2 |
| 3.7 Otras inconsistencias FK | 0 |
| 3.8 Tablas del nuevo modelo ya existentes | 0 |
| **4.x Inconsistencias del motor (total)** | **0** |
| 5.1 Group parent = Member | 0 |
| 5.3 LateralRelations fuera del enum | 0 de 0 |

# DECISIONES REQUERIDAS ANTES DEL SPRINT 1

Esta sección debe llenarse a mano por el equipo antes de ejecutar la migración real. Cada decisión se commitea junto con el script para dejar el contrato de entrada versionado.

## D1 — Members con group_id null

Regla heurística: Members cuyo role_label (case-insensitive)
contenga alguna de las palabras "asesor", "consultor", "externo",
"proveedor", "contractor" o "freelance" → persona standalone
(parent_node_id null). El resto → asignado al unit raíz de su
organización (nodo con type=unit sin parent dentro de la org).
Si la org no tiene unit raíz, la migración debe crear uno
llamado "General" con position (0, 0) antes de asignar los
Members. En esta base local: 0 casos — la regla queda
documentada para migración contra staging/prod.

## D2 — Interviews huérfanas

Descartar. Una Interview sin Member asociado es basura
referencial: no se puede migrar a NodeState porque falta el
Node de referencia. La migración debe logear cada descarte con
interview.id, interview.submitted_at y motivo "member_id
huérfano" en el log del script. En esta base local: 0 casos.

## D3 — Members huérfanos

Dos sub-reglas:
(a) Members cuya organization_id apunte a Organization
    inexistente → descartar. No hay contexto de negocio para
    reasignar. Logear con member.id, member.organization_id
    inválida y motivo "org huérfana".
(b) Members cuya organization_id sea válida pero group_id
    apunte a Group inexistente → aplicar la regla D1 (heurística
    por role_label o asignación al unit raíz de la org). Logear
    como "group reasignado por huerfanía".
En esta base local: 0 casos totales.

## D4 — Groups sin Members

Migrar igual como Node con type=unit. Un unit sin persons es
estado legítimo del modelo (área recién creada, departamento
vacante, reserva estructural). No se requiere acción especial
ni decisión manual. En esta base local: 14 casos, todos en
organizaciones de prueba ("ca" y "Laboratorio Demo"). Sin
impacto en la migración.

## D5 — Tablas del nuevo modelo preexistentes

0 colisiones detectadas en esta base local. Regla para
staging/prod: si el dry-run contra esa base reporta colisiones
en las tablas "nodes", "edges", "assessment_campaigns" o
"node_states", abortar la migración y escalar para investigar
origen (experimentos previos, ramas descartadas, corridas
locales filtradas). NO truncar ni renombrar automáticamente: el
riesgo de pérdida de datos supera el beneficio de la
automatización.

## D6 — LateralRelations con tipo "otro"

0 LateralRelations totales en esta base local. Regla para bases
con datos (Mapa de tipos "otro" al enum cerrado {lateral,
process}):
(a) Tipos con semántica de colaboración horizontal
    ("colaboración", "dependencia", "coordinación", "sinergia",
    "apoyo mutuo", o variantes) → lateral.
(b) Tipos con semántica de flujo o handoff
    ("entrada", "output", "handoff", "flujo", "proceso",
    "input", "secuencial") → process.
(c) Tipos que no encajen naturalmente en (a) ni (b) → abortar
    migración y escalar para decisión de producto. No inventar
    mapeo por defecto.
La migración debe logear cada reasignación con relation.id,
relation.type original, relation.type nuevo y regla aplicada.

## D7 — Groups con posición (0, 0) o nulls

Asignar posiciones en grilla automática durante la migración
para todos los Groups con position_x null, position_y null, o
ambos en 0. Algoritmo:
- Calcular N = ceil(sqrt(total_groups_sin_posicion))
  columnas por organización.
- Ordenar los Groups por created_at ascendente para
  determinismo.
- Posicionar en grilla: position_x = 100 + (i % N) * 250,
  position_y = 100 + floor(i / N) * 150, donde i es el índice
  0-based dentro del grupo de Groups a reposicionar de esa org.
- Spacing: 250px horizontal, 150px vertical. Origen: (100, 100).
En esta base local: 2 casos en organizaciones de prueba. El
admin puede reacomodar manualmente después en el canvas si el
auto-layout no le resulta útil. La migración debe preservar
positions existentes no-cero y no-null sin modificación.
