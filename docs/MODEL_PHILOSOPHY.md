# Filosofía del Modelo de Datos

> **Documento de referencia técnica para las capas de Estructura y Captura del canvas premium.**
> Complementa el PRD v2.1 y establece los contratos de datos que se implementarán en el refactor Node + Edge.
> En caso de conflicto, el PRD v2.1 gana.

---

## 1. Posicionamiento

Este documento describe el modelo de datos de **identidad estructural** y **captura de insumos** de la organización diagnosticada:

- **Alcance**: las capas de **Estructura** y **Captura** del canvas, que en este refactor **se unifican en una sola vista operativa**. El admin construye el organigrama, caracteriza nodos, adjunta documentos y gestiona invitaciones desde el mismo lienzo, sin cambiar de capa.
- **Fuera de alcance**: las capas **Análisis** y **Resultados** (lectura densa). Su modelo de datos, pipeline y contratos están definidos en:
  - [`MOTOR_ANALISIS.md`](./MOTOR_ANALISIS.md) — contrato del motor de análisis (tablas `analysis_runs`, `node_analyses`, `group_analyses`, `org_analyses`, `findings`, `recommendations`, `evidence_links`, `document_extractions`).
  - [`ARQUITECTURA_ANALISIS_RESULTADOS.md`](./ARQUITECTURA_ANALISIS_RESULTADOS.md) — especificación de UI de las capas Análisis y Resultados.

**Estas tablas y capas NO se modifican en este sprint.** El refactor de identidad estructural es aditivo respecto al motor: convive con él durante todo el sprint y deja una única deuda conocida (ver §9).

**Precedencia documental**:
1. PRD v2.1 gana sobre todo lo demás.
2. Si este documento entra en conflicto con el PRD, **no se resuelve aquí**: se escala al product owner para decidir.
3. Los conflictos detectados al redactar esta filosofía están listados al final de la nota de trabajo que acompaña este archivo (ver commit message / reporte del refactor).

---

## 2. Tipos de entidades

El modelo reconoce **solo dos tipos** de entidad estructural:

### 2.1 `unit`

Un **unit** es un contenedor organizacional: agrupa a personas o a otros units bajo una misma cabecera estructural.

**Ejemplos del dominio (PRD v2.1)**:
- Áreas funcionales: *Operaciones, Comercial, Finanzas, Tecnología, RRHH*.
- Equipos nominales: *Squad de Producto, Equipo de Facturación, Comité Directivo*.
- Sub-áreas: *Operaciones > Logística*, *Comercial > Ventas corporativas*.
- Órganos de gobierno de ONG: *Junta Directiva, Asamblea*.

Un unit **puede** tener otros units como hijos (sub-áreas) y **puede** tener persons como hijos (individuos asignados a esa área).

### 2.2 `person`

Una **person** es un respondiente individual: un ser humano identificado en el organigrama que, si es invitado, responderá entrevistas y aportará señales al pipeline de análisis.

**Ejemplos del dominio (PRD v2.1)**:
- *CEO, Director de Operaciones, Coordinador de Logística, Ejecutivo Comercial Junior*.
- *Gerente de Finanzas/CFO, Analista de Tesorería*.
- *Presidente de Junta, Miembro de Junta*.

Una person **siempre** cuelga estructuralmente de un unit. Una person **nunca** es raíz del organigrama. Una person **nunca** tiene hijos estructurales.

### 2.3 Por qué solo dos tipos

El refactor elimina la separación de tablas `groups` y `members` que arrastraba inconsistencias (FKs duplicados, lógica de borrado divergente, modelos visuales distintos para entidades que conceptualmente coexisten en el mismo lienzo). Colapsar a `Node { type ∈ {unit, person} }` permite:

- Un único endpoint CRUD para el canvas.
- Una única tabla de posición/estado visual.
- Jerarquía uniforme vía `parent_node_id`.
- Un único sistema de invariantes estructurales (§8).

---

## 3. Resolución del choque de nomenclatura "node"

La palabra **"node"** aparece con dos significados distintos en el repositorio. Esta sección zanja la ambigüedad **sin modificar ningún contrato existente**.

### 3.1 Los dos usos

| Uso | Documento | Significado |
|---|---|---|
| **node (legacy motor)** | `MOTOR_ANALISIS.md`, tabla `node_analyses` | Persona individual respondiente. `node_analyses` = "análisis de cada respondiente". El FK `node_analyses.group_id` apunta hoy a `groups.id`, pero el registro representa la síntesis de una persona. |
| **Node (nuevo modelo)** | este documento + refactor | Entidad unificada del organigrama, con campo `type ∈ {unit, person}`. Reemplaza `Group` y `Member` como tablas separadas. |

### 3.2 Resolución semántica

> **Cuando `MOTOR_ANALISIS.md` dice "node", conceptualmente se refiere a un `Node` con `type=person`.**

El motor de análisis **nunca** produce un `node_analysis` de un unit; su granularidad mínima es siempre una persona respondiente. Los `group_analyses` son la síntesis por unit.

### 3.3 Resolución física durante este sprint

Durante este sprint **no se tocan las tablas del motor**. Eso implica:

- `node_analyses.group_id` sigue siendo `UUID FK groups.id`.
- `group_analyses.group_id` sigue siendo `UUID FK groups.id`.
- La migración del refactor **conserva los UUIDs existentes** de `groups` y `members` al crear `nodes`, de modo que los FKs del motor siguen resolviéndose correctamente.
- Conceptualmente, la lectura correcta de `node_analyses.group_id` durante este sprint es: *"el `node_analysis` pertenece al unit que contiene al respondiente"*. Pero físicamente el FK sigue apuntando a la tabla legacy `groups`.

Esta inconsistencia entre semántica y física es **deuda técnica conocida y documentada** (ver §9.3). Se resolverá en un sprint posterior renombrando los FKs del motor a `node_id` y repointing a `nodes.id`.

---

## 4. Mecanismos de relación: composición vs. relación tipada

El modelo distingue dos mecanismos de relación estructural, **que no se pueden mezclar**.

### 4.1 Composición jerárquica → `parent_node_id`

- Vive en la misma tabla `nodes`, como columna self-referential `parent_node_id UUID NULL FK nodes.id`.
- Representa la **cadena de autoridad o pertenencia organizacional**: "este unit es subárea de aquel"; "esta person pertenece a ese unit".
- Define un **árbol** (ver invariantes §8.4 y §8.5).
- Se dibuja en el canvas como un connector jerárquico (línea sólida vertical/curva estándar).

### 4.2 Relación tipada → `edges`

- Vive en tabla separada `edges` con `source_node_id`, `target_node_id`, `edge_type`, `edge_metadata`, `organization_id`, `created_at`, `deleted_at`.
- Representa **relaciones funcionales horizontales** entre units: colaboración, dependencia, flujo de información, etc.
- Los valores permitidos de `edge_type` son un enum cerrado: **`lateral`** y **`process`**. No existe un valor de escape tipo `"other"` / `"otro"`: si aparece un caso real que no cabe, es señal para agregar un tipo nuevo con semántica explícita, no para abrir un cajón de sastre. Lo inmutable además es que **no existe el tipo `hierarchical`** (la jerarquía vive en `parent_node_id`, ver §4.3).
- `edge_metadata`: jsonb NOT NULL DEFAULT '{}'. Metadata libre del edge. Uso principal: edges de tipo "process" almacenan aquí el campo "order" (entero positivo) exigido por la invariante 13 de §8. Futuros tipos de edge pueden agregar campos sin cambiar schema.
- `deleted_at`: timestamptz nullable, default null. Marca de soft-delete para preservar integridad referencial con `evidence_links` del motor.
- Se dibuja en el canvas con estilos visuales distintos del connector jerárquico (línea punteada, color accent según tipo, etiqueta opcional).

### 4.3 Regla explícita

> **NO existen edges de tipo `hierarchical`. La jerarquía vive exclusivamente en `parent_node_id`.**

Motivación:
- Evitar dos fuentes de verdad para la misma relación.
- Permitir tests estructurales (detección de ciclos, cálculo de raíces, validación de que toda person cuelga de un unit) con una sola consulta recursiva sobre `nodes`.
- Dejar `edges` libre para representar exclusivamente la red funcional, que es la que interesa al pipeline de análisis (métricas de red, nodos puente, nodos aislados — ver `MOTOR_ANALISIS.md §2, tabla `org_analyses.network_metrics`).

### 4.4 Restricción de arity de edges

En este modelo, **los edges conectan solo units entre sí**. No hay edges person↔person ni person↔unit. Las relaciones de una persona con la organización se infieren desde `parent_node_id` y desde sus `node_states` por campaña. Ver invariante §8.6.

---

## 5. Estado vs. identidad

El modelo separa dos planos de información por nodo. Esta separación es **no negociable**: cualquier dato que cambie entre diagnósticos debe vivir en `node_states` o en una tabla equivalente, **nunca en `nodes`**.

### 5.1 Tabla `nodes` — identidad permanente

Información que define qué/quién es el nodo, independiente de cualquier campaña de diagnóstico:

- `id` — UUID primario, inmutable.
- `organization_id` — pertenencia organizacional.
- `parent_node_id` — posición en el árbol estructural.
- `type` — `unit` o `person`.
- `name` — nombre canónico del unit o de la persona.
- `position_x`, `position_y` — posición visual en el canvas de Estructura/Captura (ver nota en §5.3).
- `attrs` (columna `Node.attrs`): jsonb NOT NULL DEFAULT '{}'. Metadata libre del nodo. No debe contener campos que deban ser queryables o indexables (esos se promocionan a columnas dedicadas). Tampoco debe contener secrets ni PII no necesaria.
- `created_at`: timestamptz NOT NULL.
- `deleted_at`: timestamptz nullable, default null. Marca de soft-delete. Los queries del canvas filtran `WHERE deleted_at IS NULL`. Preserva integridad referencial con tablas del motor de análisis que referencian `Node` por UUID.

### 5.1.1 Campos legacy en `Node.attrs` durante coexistencia

Durante el período de coexistencia entre el modelo viejo (Group, Member) y el nuevo (Node), varios campos que existían como columnas en las tablas viejas se alojan temporalmente en Node.attrs porque no se promovieron a columnas dedicadas del nuevo modelo:

Para Nodes espejados desde Group (type=unit):
- description: descripción del grupo.
- tarea_general: tarea principal del área.
- area: sub-área o división.
- nivel_jerarquico: nivel en la estructura.
- tipo_nivel: tipo del nivel jerárquico.
- is_default: marca de grupo por defecto.
- node_type (legacy): tipo de grupo del modelo viejo.

Para Nodes espejados desde Member (type=person):
- role_label: rol reportado del miembro.
- interview_token: token de entrevista legacy (ahora respondent_token en NodeState, pero preservado en attrs por consistencia de migración).
- token_status: estado del token.
- email: email del miembro, si la columna existe en Member.

Estos campos son DEUDA TEMPORAL. Criterios para promover uno a columna dedicada de Node:
- Se consulta frecuentemente en queries (requiere índice).
- Es semánticamente central al Node (no metadata libre).
- Tiene tipo estricto que JSONB no valida bien.

La promoción se decide caso por caso en sprints futuros, trackeada en DEUDA_DOCUMENTAL.md.

### 5.2 Tabla `node_states` — estado por campaña

Información que cambia entre diagnósticos y debe ser recuperable históricamente:

- `id` — UUID primario.
- `node_id` — FK a `nodes.id`.
- `campaign_id` — FK a `assessment_campaigns.id`.
- `email_assigned` — email del respondiente (solo aplica a persons).
- `role_label` — cargo/rol reportado en esta campaña (puede evolucionar).
- `context_notes` — contexto libre del admin específico a esta campaña.
- `respondent_token` — token regenerado por campaña para identificar al respondiente en la URL pública (solo persons). Nombre sin prefijo `interview_` por consistencia con `status`: `NodeState` puede contener estado de otras evaluaciones en el futuro.
- `status` — enum cerrado `{invited, in_progress, completed, skipped}` (ver semántica en §5.2.1). El nombre `status` (sin prefijo) es canónico porque `NodeState` puede contener estado de otras evaluaciones además de entrevistas en el futuro.
- `invited_at`, `completed_at`.

`UNIQUE (node_id, campaign_id)` — un nodo tiene a lo sumo un estado por campaña.

#### 5.2.1 Semántica del enum `NodeState.status`

- **`invited`**: NodeState creado, respondiente no entró todavía.
- **`in_progress`**: respondiente entró y hay `interview_data` parcial.
- **`completed`**: respondiente submitteó (`completed_at` no null).
- **`skipped`**: admin excluyó explícitamente este node de la campaña (ej: persona en vacaciones, rol sin respondiente asignado).

### 5.3 Casos frontera y decisiones

- **`position_x`, `position_y`** viven hoy en `nodes` porque la posición visual se comparte entre todas las capas de Estructura/Captura y en la práctica es semi-permanente. Si el producto permite re-layouts por campaña en el futuro, migra a `node_states`. Flagged como decisión revisable.
- **`name`** es identidad. Renombrar un unit o una person no crea un nuevo nodo; es un UPDATE excepcional sobre `nodes.name`. Cambios de cargo frecuentes usan `node_states.role_label`.
- **`email_assigned`** NO vive en `nodes`. Un respondiente puede cambiar de email entre campañas, o la misma person puede tener distintos responsables por campaña.

---

## 6. Longitudinalidad — `AssessmentCampaign` como entidad central

El producto soporta múltiples diagnósticos sobre la misma organización a lo largo del tiempo (PRD v2.1 — comparación temporal, Fase 5). El modelo hace esto de primera clase.

### 6.1 Tabla `assessment_campaigns`

- `id` — UUID primario.
- `organization_id` — FK.
- `name` — etiqueta humana (ej: *"Diagnóstico Q1 2026"*).
- `status` — `draft | active | closed`.
- `started_at`, `closed_at` — `closed_at` alinea con el estado terminal `status='closed'` del enum `CampaignStatus`; no hay estado `'ended'`.
- `created_by_user_id` — UUID, FK a `users.id`, nullable (SET NULL). Usuario que creó la campaña. Auditoría de quién lanzó cada diagnóstico; útil para reportes longitudinales y para filtrar campañas por creador en dashboards internos.

> **Schema desde Sprint 1, UI desde Sprint 3 (decisión del 21 de abril de 2026).** El schema de `Campaign` existe desde Sprint 1 (tabla, endpoints mínimos, migración inicial). La UI NO expone la noción de campañas múltiples hasta Sprint 3: durante Sprint 1–2 el admin ve una única "Diagnóstico Inicial" implícita. La migración inicial crea automáticamente una `AssessmentCampaign` por organización con `status = "active"` y `name = "Diagnóstico Inicial"`, y asocia todos los `node_states`, entrevistas y runs existentes a esa campaña. Esto preserva opcionalidad de longitudinalidad sin adelantar funcionalidad visible.

### 6.2 Reglas

- **Múltiples campañas por organización** son el caso normal, no excepcional.
- **Una sola campaña `active` por organización** a la vez (invariante §8.11). `draft` y `closed` pueden coexistir.
- Toda **entrevista, `node_state`, `analysis_run`, `diagnosis_result`** referencia su `campaign_id`. Esto permite comparación temporal sin mezclar datos.
- La **estructura organizacional** (la tabla `nodes` y sus `parent_node_id`) es **transversal a campañas**: un cambio en el organigrama se refleja inmediatamente en todas las campañas no cerradas.

### 6.3 Documentos: permanentes vs. de campaña

La tabla `documents` admite dos modos:

| Modo | `campaign_id` | Semántica |
|---|---|---|
| **Permanente** | `NULL` | Documento institucional perdurable (estatutos, misión, manual de procesos). Participa en todas las campañas posteriores a su fecha de creación. |
| **De campaña** | no nulo | Documento específico de ese diagnóstico (ej: reporte financiero de un trimestre puntual). Solo participa en esa campaña. |

Esta distinción es la que hoy usa implícitamente `document_extractions.run_id` del motor, pero promovida a metadato de primera clase sobre el documento mismo.

---

## 7. Convención visual del canvas (Estructura + Captura unificadas)

**Esta sección aplica solo a la vista unificada de Estructura y Captura.** Las capas Análisis y Resultados mantienen las convenciones de [`ARQUITECTURA_ANALISIS_RESULTADOS.md`](./ARQUITECTURA_ANALISIS_RESULTADOS.md) sin modificación.

### 7.1 Nodos

- **unit**: tarjeta rectangular redondeada, tamaño estándar, color neutro con acento del área. Nombre del unit en tipografía display. Badge con número de hijos directos (`unit` + `person`).
- **person**: tarjeta más pequeña, forma sutilmente distinta (chip ovalado o rectángulo más estrecho), con avatar-placeholder o inicial. Nombre + `role_label` del estado de la campaña activa.
- **Nodo sin email asignado (person)**: borde punteado amarillo + tooltip *"Asigna un email en este panel para invitar"*.
- **Nodo con entrevista completada (person)**: check verde discreto en esquina.
- **Nodo con entrevista en progreso (person)**: spinner o indicador de progreso.

### 7.2 Relaciones

- **Composición (`parent_node_id`)**: línea sólida gris clara, vertical/curva estándar React Flow. No tiene etiqueta.
- **Edge tipado**: línea punteada, color según `edge_type` (`lateral` / `process`), con etiqueta opcional al hover.

### 7.3 Panel lateral contextual (único para ambas capas antes unificadas)

Al hacer clic en un nodo, el panel lateral muestra pestañas:

- **Identidad** — `name`, `type`, `parent_node_id`.
- **Estado de campaña** — campos de `node_states` de la campaña activa: `email_assigned`, `role_label`, `context_notes`, `status` (ver §5.2.1), token copiable, botón WhatsApp (solo persons).
- **Documentos** — adjuntos al nodo (si aplica en el roadmap).

Esta unificación en un solo panel reemplaza la dualidad *Estructura (edición) / Recolección (lectura de estado)* del PRD v2.1 sección 7.

> **Decisión final (21 de abril de 2026):** tres capas oficiales — **Estructura+Captura**, **Análisis**, **Resultados**. La antigua "Recolección" se fusiona en "Estructura+Captura". CLAUDE.md §3 y el PRD v2.1 §7 deben actualizarse para reflejar esta oficialización.

---

## 8. Invariantes del modelo

Lista numerada de las **13 invariantes** que se enforzan en validación server-side. Estas invariantes son la referencia para los tests del Sprint 1.

1. **Scope organizacional**. Todo `Node`, `Edge`, `NodeState`, `AssessmentCampaign` y `Document` tiene exactamente una `organization_id`. Ninguna FK cruza organizaciones: si una FK apunta a un recurso, ese recurso debe pertenecer a la misma organización.

2. **Tipo discreto**. `Node.type ∈ {"unit", "person"}`. No hay subtipos, ni valores libres, ni extensión polimórfica.

3. **Jerarquía de persons**. Todo `Node` con `type = "person"` tiene `parent_node_id` **no nulo**, y el nodo padre tiene `type = "unit"`. No existen persons raíz. No existen persons hijos de persons.

4. **Jerarquía de units**. Un `Node` con `type = "unit"` puede tener `parent_node_id` nulo (raíz organizacional) o apuntar a otro `Node` con `type = "unit"`. Nunca apunta a una person.

5. **Acíclico**. La relación `parent_node_id` define un árbol sin ciclos. Server-side valida esto en cualquier operación que modifique `parent_node_id`.

6. **Edges inter-unit exclusivos**. `Edge.source_node_id` y `Edge.target_node_id` apuntan ambos a nodos con `type = "unit"`. No existen edges que toquen persons.

7. **No self-loop, unicidad dirigida**. Un `Edge` cumple `source_node_id != target_node_id`. No se admiten dos edges con la misma tripleta `(source_node_id, target_node_id, edge_type)`.

8. **Enum cerrado de `Edge.edge_type`**. Los únicos valores válidos son `"lateral"` y `"process"`. No existe `"hierarchical"` (la jerarquía vive en `parent_node_id`) ni valores fallback tipo `"other"` / `"otro"`. Cualquier intento de crear un edge con un tipo fuera del enum es rechazado server-side.

9. **Identidad inmutable por campaña**. Los campos `id`, `type`, `organization_id` de `nodes` no se modifican vía UPDATE en el ciclo normal de una campaña. Cualquier atributo que cambie entre diagnósticos (email asignado, role_label operativo, context_notes) vive en `node_states`, nunca en `nodes`.

10. **NodeState por campaña único**. La tabla `node_states` satisface `UNIQUE (node_id, campaign_id)`. Un nodo tiene a lo sumo un estado por campaña.

11. **Campaña activa única**. Por cada `organization_id`, existe a lo sumo UNA `AssessmentCampaign` con `status = "active"` simultáneamente. `draft` y `closed` pueden coexistir sin restricción.

12. **Documentos consistentes**. Un `Document` pertenece a una organización. Si tiene `campaign_id` no nulo, ese campaign debe pertenecer a la misma organización (`documents.organization_id = campaigns.organization_id`). Un documento con `campaign_id NULL` es permanente y participa en todas las campañas posteriores a su `created_at`.

13. **Orden requerido en edges `process`**. Edges con `edge_type='process'` deben tener un campo `'order'` entero positivo en `edge_metadata`. Edges con `edge_type='lateral'` pueden tener `edge_metadata` vacío (`{}`). La validación se ejecuta server-side antes de persistir el edge.

### 8.1 Niveles de enforcement de las invariantes

Las 13 invariantes documentadas se enforzan en niveles distintos según la etapa del refactor:

**Nivel 1 — Router:** la validación vive en los endpoints FastAPI. Cualquier request que viole una invariante recibe `422` (o `409` cuando aplica conflicto de estado). Este nivel asume que *todas* las escrituras pasan por el router autenticado.

**Nivel 2 — Base de datos:** las invariantes críticas se espejan en `CHECK constraints`, `UNIQUE` parciales y triggers PL/pgSQL de PostgreSQL. Escribir por fuera del router (ORM directo, SQL crudo, scripts de datos, compat layer) es rechazado por la DB.

**Estado por invariante (actualizado Sprint 2.1, commit de migración `20260421_0009_invariantes_db`):**

| Inv | Nombre | Nivel 1 (router) | Nivel 2 (DB) | Mecanismo DB |
|---|---|---|---|---|
| 1  | Scope organizacional (org_id NOT NULL en Node) | sí | sí | `NOT NULL` desde Sprint 1.1 |
| 2  | Parent mismo org | sí | sí | Trigger `trg_nodes_parent_same_org` |
| 3  | Jerarquía de persons / unit no tiene parent person | sí | sí | Trigger `trg_nodes_unit_parent_is_unit` |
| 4  | Jerarquía de units (no self-loop y cross-type en parent) | sí | parcial | self-loop vía `check_edge_source_ne_target` (edges). Self-parent de Node queda router-only. |
| 5  | Acíclico | sí | no | Requiere CTE recursiva — queda router-only |
| 6  | Edges inter-unit y misma org | sí | sí (org) | Trigger `trg_edges_nodes_same_org`. El sub-requisito "ambos son unit" queda router-only. |
| 7  | No duplicado `(source, target, edge_type)` | sí | no | Conflicto con `edge_metadata.order` en process edges — pendiente de resolución (ver `DEUDA_DOCUMENTAL.md`). |
| 8  | Enum cerrado `edge_type` | sí | sí | Native PostgreSQL `ENUM edge_type_enum` |
| 9  | Identidad inmutable por campaña | sí | no | Validación semántica sobre PATCH — queda router-only |
| 10 | NodeState UNIQUE (node_id, campaign_id) | sí | sí | `UNIQUE` desde Sprint 1.1 |
| 11 | Campaña activa única | sí | sí | Partial unique index `uniq_one_active_campaign_per_org` |
| 12 | Documents consistentes | sí | no | Requiere validación multi-tabla — queda router-only |
| 13 | Orden requerido en edges `process` | sí | no | Validación semántica sobre JSONB — queda router-only |

**Capa de compatibilidad y Nivel 2 (Sprint 2.1):** los routers legacy `groups.py`, `members.py`, `interviews.py`, `interview_public.py` escriben sobre `nodes` / `node_states` sin pasar por el router nuevo. Desde Sprint 2.1 el Nivel 2 está activo para las invariantes 2, 3, 4 (edge self-loop), 6 (misma org) y 11: si un router legacy materializa un dato inválido sobre esas invariantes, la DB lo rechaza y la operación falla ruidosamente en vez de corromper silenciosamente.

Las invariantes que quedan router-only (5, 7, 9, 12, 13 y el sub-requisito "ambos nodos son unit" de la 6) siguen cubiertas por los propios routers legacy, que aplican sus validaciones equivalentes antes de espejar (ej. un `Member` solo puede tener `group_id` válido, lo que al espejarse genera un person hijo de unit, respetando la invariante 3).

**Política para tests de invariantes:** cada test de invariante debe declarar explícitamente qué nivel ejercita:

- Test de "nivel router" (`test_router_*`) → hace request HTTP y espera `422` / `409`.
- Test de "nivel DB" (`test_db_*`) → escribe directo con el ORM / SQL crudo y espera `IntegrityError` o `CheckViolation`.

Mientras una invariante no tenga constraint de DB, los tests `test_db_*` quedan marcados `@pytest.mark.xfail` con razón explícita (p. ej. "invariante router-only por validación semántica sobre JSONB"). Esto deja la deuda visible en el suite en vez de ocultarla.

---

## 9. Coexistencia con el motor de análisis durante este sprint

El refactor Node + Edge **convive** con el motor de análisis durante este sprint sin romperlo. Esta sección formaliza el contrato de coexistencia.

### 9.1 Tablas del motor que NO se modifican

- `analysis_runs`
- `node_analyses`
- `group_analyses`
- `org_analyses`
- `findings`
- `recommendations`
- `evidence_links`
- `document_extractions`
- `diagnosis_results`

Sus columnas, sus FKs y sus constraints permanecen exactamente como están definidos en [`MOTOR_ANALISIS.md`](./MOTOR_ANALISIS.md).

### 9.2 Preservación de UUIDs

La migración del refactor crea la tabla `nodes` **preservando los UUIDs** de los registros existentes en `groups` y `members`:

- Cada fila de `groups` se convierte en una fila de `nodes` con `type = "unit"` y el mismo `id`.
- Cada fila de `members` se convierte en una fila de `nodes` con `type = "person"` y el mismo `id`, con `parent_node_id = members.group_id`.

Esto implica que:

- `node_analyses.group_id` sigue resolviéndose: apunta a un UUID que ahora también existe en `nodes` con `type = "unit"` (y sigue existiendo en `groups` hasta el sprint que la elimine).
- `group_analyses.group_id` se comporta igual.
- `diagnosis_results.structure_snapshot` (JSONB) puede seguir teniendo UUIDs que existen en ambas tablas durante la ventana de coexistencia.

### 9.3 Pipeline sin cambios

El pipeline de 4 pasos del motor sigue funcionando exactamente igual:

- El scoring cuantitativo se ejecuta sobre entrevistas ingresadas, igual que hoy.
- Los prompts de los pasos 1–4 siguen recibiendo `group_id` como referencia de agrupación.
- `evidence_links.node_analysis_id` y `evidence_links.group_analysis_id` siguen siendo trazables.
- No se requiere ningún cambio en `backend/scripts/generate_mock_analysis.py` ni en el consumer externo (Codex).

### 9.4 Deuda técnica conocida y documentada

Cuando, en un sprint posterior, se elimine la tabla legacy `groups`, habrá que:

1. Renombrar `node_analyses.group_id` → `node_analyses.node_id` y repointear el FK a `nodes.id`.
2. Renombrar `group_analyses.group_id` → `group_analyses.node_id` y repointear el FK a `nodes.id` (filtrando por `nodes.type = "unit"` en consultas).
3. Actualizar `findings.node_ids` y `recommendations.node_ids` (JSONB con UUIDs): los UUIDs ya son correctos porque se preservaron, pero la documentación de qué tabla referencian debe actualizarse.
4. Actualizar [`MOTOR_ANALISIS.md`](./MOTOR_ANALISIS.md) §2 para reflejar los nuevos FKs.

Esta es la **única deuda que deja este refactor**. Está aislada, es acotada y no bloquea ningún flujo de producto mientras `groups` exista en paralelo.

---

*Actualizado: Abril 2026 | Versión: 1.0*
*Referencia: PRD v2.1 | CLAUDE.md | MOTOR_ANALISIS.md | ARQUITECTURA_ANALISIS_RESULTADOS.md*
