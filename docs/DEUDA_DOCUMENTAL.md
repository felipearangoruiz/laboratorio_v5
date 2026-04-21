# Deuda Documental

> Tracker formal de secciones de la documentación que quedarán obsoletas cuando aterricen sprints posteriores del refactor Node + Edge.
> Cada fila representa una actualización pendiente que NO se aplica ahora para respetar las reglas de no-rotura del sprint vigente.

---

## Cómo usar este tracker

- Al cerrar cada sprint, revisar las filas cuyo **Sprint estimado** coincida y aplicar los cambios.
- Al agregar deuda nueva: apendar fila al final, referenciando el documento y la sección específica.
- Al resolver deuda: marcar la fila como ~~tachada~~ (no borrar) y agregar un ítem en el registro de cambios al final, con fecha y commit.

---

## Deuda abierta

| # | Archivo | Sección | Cambio pendiente | Sprint estimado |
|---|---|---|---|---|
| 1 | `CLAUDE.md` | §3 "Reglas fundamentales" rule 3 | ~~Actualizar "4 capas" → "3 capas: Estructura+Captura / Análisis / Resultados"~~ | ~~Sprint 1~~ **Resuelta 2026-04-21** |
| 2 | `CLAUDE.md` | §3 bloques "CAPA ESTRUCTURA" y "CAPA RECOLECCIÓN" | ~~Fusionar en un único bloque "CAPA ESTRUCTURA+CAPTURA"~~ | ~~Sprint 1~~ **Resuelta 2026-04-21** |
| 3 | `CLAUDE.md` | §6 "Modelo de datos" | ~~Reescribir: Group/Member separados → Node unificado; LateralRelation → Edge enum cerrado; agregar NodeState y AssessmentCampaign~~ | ~~Sprint 1~~ **Resuelta 2026-04-21** |
| 4 | `docs/MOTOR_ANALISIS.md` | §2 tabla `node_analyses`, columna `group_id` | Renombrar `group_id UUID FK groups` → `node_id UUID FK nodes` una vez que la tabla `groups` se elimine. El `node_id` referencia siempre un respondiente (semánticamente `nodes.type = "person"`, aunque físicamente durante Sprint 1 apunte al unit contenedor — ver `MODEL_PHILOSOPHY.md` §3). | Sprint en que se elimine `groups` (post Sprint 2) |
| 5 | `docs/MOTOR_ANALISIS.md` | §2 tabla `group_analyses`, columna `group_id` | Renombrar `group_id UUID FK groups` → `node_id UUID FK nodes`, filtrando por `nodes.type = "unit"` en consultas. | Sprint en que se elimine `groups` (post Sprint 2) |
| 6 | `docs/MOTOR_ANALISIS.md` | §2 tabla `findings`, columna `node_ids` | Clarificar en la descripción que los UUIDs referencian `nodes.id` (no `groups.id`). Los UUIDs ya son correctos porque la migración los preserva; solo la anotación textual queda desactualizada. | Sprint en que se elimine `groups` (post Sprint 2) |
| 7 | `docs/MOTOR_ANALISIS.md` | §2 tabla `recommendations`, columna `node_ids` | Misma nota que fila 6: clarificar que el FK lógico es `nodes.id`. | Sprint en que se elimine `groups` (post Sprint 2) |
| 8 | `docs/MOTOR_ANALISIS.md` | §1 "PASO 1 — Extracción por nodo" | El término "nodo/node" en este documento queda resignificado por `MODEL_PHILOSOPHY.md` §3. El disclaimer al inicio ya apunta a esa resolución; revisar si hace falta reforzarlo en las subsecciones de cada paso del pipeline. | Post Sprint 2 |
| 9 | `docs/ARQUITECTURA_ANALISIS_RESULTADOS.md` | §1 tabla "Capa \| Naturaleza" | Eliminar fila *"Recolección \| Captura"* — esa capa se fusiona en *"Estructura \| Captura"*. Renombrar primera fila a *"Estructura+Captura \| Captura"*. | Sprint en que se implemente UI unificada (Sprint 2 estimado) |
| 10 | `docs/ARQUITECTURA_ANALISIS_RESULTADOS.md` | §8 árbol ASCII de "Estados de la UI por capa" | Revisar si el árbol hace referencia a "Recolección" como capa separada. Actualmente solo describe Análisis y Resultados, pero confirmar al actualizar la fila 9. | Sprint en que se implemente UI unificada (Sprint 2 estimado) |
| 11 | `docs/PRD_v2_1.md` | §7.3 — arquitectura de capas | ~~Oficializar "3 capas" en el documento maestro de producto. Decisión tomada el 2026-04-21; pendiente bajar al PRD cuando el product owner actualice el archivo fuente.~~ **Resuelta 2026-04-21** — PRD v2.2 incorpora en §7.3 el cambio de cuatro a tres capas con nota `> **Actualizado v2.2 (decisión A1)**`. | ~~Antes de cerrar Sprint 1~~ |
| 12 | `docs/PRD_v2_1.md` | §12 — modelo de datos | ~~Si el PRD describe explícitamente `Group` / `Member` / `LateralRelation` como entidades separadas, actualizar para reflejar el refactor Node+Edge. Verificación requiere pasada humana con el PRD abierto; Claude Code no puede parsear el .docx.~~ **Resuelta 2026-04-21** — PRD v2.2 §12 contiene la tabla unificada con `Node (type: unit\|person)`, `Edge (edge_type: lateral\|process)`, `AssessmentCampaign`, `NodeState`. El changelog interno documenta la transición de Group/Member/LateralRelation. | ~~Antes de cerrar Sprint 1~~ |
| 13 | `CLAUDE.md` | §2 "Modelos existentes" (línea 28) | ~~La lista `User, Organization, Group, Member, Interview, AnalysisJob` queda desactualizada al aterrizar el refactor. Reemplazar por la lista canónica del Sprint 1 una vez migrado.~~ **Parcialmente resuelta 2026-04-21** — se agregó nota inline apuntando a MODEL_PHILOSOPHY.md. Reescribir el listado principal cuando el refactor esté en `main`. | Sprint 1 post-migración |
| 14 | `CLAUDE.md` | §8 Fase 1 "Canvas y estructura" | ~~Actualizar bullets para reflejar Node, Edge, NodeState, AssessmentCampaign en vez de "Migrar Group", "Modelo LateralRelation".~~ | ~~Sprint 1~~ **Resuelta 2026-04-21** |
| 15 | `docs/MOTOR_ANALISIS.md` / `CLAUDE.md` §12 | referencias al "motor nunca envía datos crudos" | Revisar que ningún ejemplo/prompt cite entidades obsoletas (Member, Group como clases) — el pipeline es agnóstico a esas tablas, pero la documentación de contratos podría citar nombres que cambien. Auditoría ligera recomendada. | Post Sprint 2 |

---

## Registro de cambios aplicados

| Fecha | Ítem(s) resueltos | Commit / Referencia |
|---|---|---|
| 2026-04-21 | #1, #2, #3, #14, #13 (parcial) | Commit del sprint "decisiones A1–A4 aplicadas". Introducción del refactor Node + Edge en documentación. |
| 2026-04-21 | #11, #12 | El PRD se actualizó a **v2.2** incorporando las cuatro decisiones A1–A4 del Sprint 0. El changelog completo (incluyendo A1: tres capas; A2: AssessmentCampaign en schema Sprint 1; A3: enum cerrado de Edge a `lateral`/`process`; A4: Member absorbido en Node con `type=person`) vive dentro del propio PRD en la sección "Changelog v2.1 → v2.2". El archivo mantiene el nombre `docs/PRD_v2_1.md` en disco por compatibilidad con referencias existentes en `MODEL_PHILOSOPHY.md` y otros documentos; la versión interna es v2.2. |
| 2026-04-21 | Alineación post-dry-run | Alineación PRD ↔ MODEL_PHILOSOPHY post-dry-run: (1) `Edge.edge_metadata` confirmada como columna canónica (jsonb NOT NULL DEFAULT '{}'). Vive el campo "order" de los edges tipo "process". (2) `NodeState.status` canonizado (se descarta `interview_status` como nombre). (3) `NodeState.status` enum cerrado a `{invited, in_progress, completed, skipped}` con semántica documentada. Ambos puntos quedan reflejados en `docs/MODEL_PHILOSOPHY.md` (§4.2 y §5.2.1) y en `docs/PRD_v2_1.md` (v2.2 interno, §12 tabla de modelo de datos). Sin deuda residual sobre este tema. |

---

*Creado: 21 de abril de 2026 | Responsable: tracker colectivo del equipo*
