# Sprint 2.3 — Cierre formal del intento original

> Documento de cierre del Sprint 2.3 tal como estaba originalmente especificado.
> El sprint se pausó durante el análisis; no se escribió código ni se hicieron commits.
> Esta nota formaliza por qué el alcance se reformula dentro del rediseño de visión del 21 de abril de 2026.
>
> Ver también: `docs/MODEL_PHILOSOPHY.md` §5.1.2, §5.2.2, §7 — visión nueva.
> `docs/PRD_v2_1.md` §7.3, §7.4, §7.8 — capa Estructura (unificada, canvas + panel).
> `docs/DEUDA_DOCUMENTAL.md` — registro del rediseño.

---

## 1. Objetivo original del 2.3

Migrar `frontend/app/org/[orgId]/canvas/page.tsx`, `SidePanel.tsx` y `CollectionPanel.tsx` desde los endpoints legacy (`/groups`, `/members`, `/interviews`) hacia los endpoints nuevos del refactor (`/nodes`, `/edges`, `/node-states`), **sin cambios visuales ni cambios de feature**. El sprint era una migración mecánica.

---

## 2. Por qué se pausó

El análisis previo a escribir código reveló tres bloqueos de fondo que hacían imposible la regla "zero visual changes, zero feature changes". Se documentan aquí para que ningún agente futuro reintente la migración 1:1 sin replantearla antes.

### Bloque 1 — Forma del dato: árbol anidado vs. lista plana

- `getOrgGroups` (legacy) devuelve árbol anidado con `member_count`, `tarea_general`, `area`, `nivel_jerarquico`, `description` como campos de primer nivel del objeto.
- `GET /nodes` (nuevo) devuelve lista plana. El parent se infiere de `parent_node_id`. Los campos ricos legacy viven en `attrs` (jsonb) — no están promovidos a columnas.
- No hay equivalente server-side de `member_count`.
- El discriminador cambia: `node_type ∈ {person, area}` → `type ∈ {person, unit}`. Cada `switch` o comparación del frontend necesita rename simultáneo al cambio de endpoint.

Implicación: no es refactor de endpoint, es refactor del shape del estado del canvas en todo el árbol de componentes.

### Bloque 2 — Cambio de cardinalidad N→1 y falta de contexto de campaña

- `getNodeInterviews` (legacy) devuelve array: **una Interview por cada Member de cada Group**.
- `NodeState` (nuevo) es 1:1 por `(node, campaign)`.
- Cambio semántico real, no renombre. Lo que antes era N entrevistas por nodo, ahora es un único NodeState por (nodo, campaña).
- El frontend no tiene concepto de "campaña activa". Hasta que exista, cualquier consulta de NodeState pide un `campaign_id` que nadie sabe de dónde sacar.
- `inviteFromNode`, `revokeInvitation`, `sendReminder` en backend siguen operando sobre `member_id` legacy. Migrarlos requiere endpoints nuevos basados en NodeState, no existe aún.

Implicación: la migración no cierra si no se resuelven primero (a) el concepto de campaña en frontend (resuelto ahora por la "Campaña Activa Implícita" de `MODEL_PHILOSOPHY.md` §5.2.2), y (b) los endpoints backend de invitar/revocar/recordar basados en NodeState.

### Bloque 3 — La pestaña "Members" del SidePanel pierde sentido

- El SidePanel tiene una pestaña "Members" que lista Members de un Group. Esa división es coherente en el modelo viejo (tablas separadas).
- En el modelo nuevo, un miembro = un `Node` con `type=person` y `parent_node_id=area.id`. La "pestaña Members" deja de ser una pestaña y se colapsa en "lista de nodos hijos del unit seleccionado".
- No es migración de datos; es rediseño UX.

Implicación: tocar el SidePanel sin cambios visuales es imposible. O se cambia UX (y deja de ser migración mecánica), o no se toca y queda inconsistente con el modelo nuevo.

---

## 3. Conclusión

La regla "zero visual changes, zero feature changes" del 2.3 original es incompatible con la realidad del gap entre los dos modelos. La migración se **difiere** hasta:

1. **Visión reframeada** (hecha en este sprint): capa única "Estructura" con arquitectura canvas + panel contextual, estado calculado para areas, notas permanentes en `Node.attrs.admin_notes`, campañas fuera de la UX. Ver `docs/MODEL_PHILOSOPHY.md` §5.1.2, §5.2.2, §7 y `docs/PRD_v2_1.md` §7.3.
2. **Endpoints backend basados en NodeState** para invitar, revocar y recordar, apuntando a la Campaña Activa Implícita por defecto.
3. **Concepto de "Campaña Activa Implícita" en frontend** (hook u contexto) que resuelva el `campaign_id` automáticamente para todas las queries de `/node-states`.

Una vez esos tres elementos existan, los prompts originales 2.3, 2.4 y 2.5 se rediseñan desde la visión nueva — no se ejecutan tal como estaban especificados.

---

*Cierre: 21 de abril de 2026. Autor: equipo de refactor.*
