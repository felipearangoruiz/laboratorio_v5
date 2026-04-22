# CLAUDE.md — Laboratorio de Modelamiento Institucional con IA

> **Este archivo es la guía principal para Claude Code.**
> Léelo completo antes de ejecutar cualquier tarea.

---

## 1. Qué es este proyecto

Una plataforma web que permite a líderes organizacionales (CEOs, directores, gerentes de ONG) diagnosticar cómo funciona su organización internamente, combinando estructura organizacional + entrevistas a miembros + análisis con IA.

**Fuente de verdad:** `docs/PRD_v2.1_Diagnostico_Organizacional.docx` — este PRD gobierna todas las decisiones. Si hay conflicto entre este archivo, el código existente o cualquier otro documento, el PRD v2.1 gana.

**Documento de arquitectura UI:** `docs/ARQUITECTURA_ANALISIS_RESULTADOS.md` — especificación completa de las capas Análisis y Resultados del canvas.

**Documento secundario (referencia técnica):** Eliminado (`docs/ARCHITECTURE_V1_FINAL.md`). El PRD v2.1 es la única fuente de verdad de producto.

---

## 2. Estado actual del repositorio

### ✅ Conservar (backend)

El backend tiene una base funcional que debe mantenerse y extenderse:

- **Stack:** FastAPI + SQLModel + PostgreSQL + Alembic (migraciones) + Docker
- **Auth:** JWT con access + refresh token. Login, logout, /me. Funciona.
- **Modelos existentes:** User, Organization, Group, Member, Interview, AnalysisJob. Necesitan ajustes (ver sección 6) pero la estructura es sólida. *(Nota del refactor Node+Edge — Sprint 1: `Group` se absorbe como `Node type=unit`; `Member` como `Node type=person`; `LateralRelation` se reemplaza por `Edge` con enum cerrado `{lateral, process}`. Ver `docs/MODEL_PHILOSOPHY.md` para el modelo nuevo.)*
- **Routers existentes:** auth, organizations, groups, members, interviews, interview_public. Funcionan.
- **Docker Compose:** PostgreSQL 16 + backend + frontend. Funciona.
- **Seed:** Crea organización default + superadmin.
- **Banco de preguntas:** `backend/app/questions.py` — 15 preguntas en 5 lentes. Debe migrarse a 8 dimensiones según PRD.

### ❌ Descartar (frontend completo)

El frontend actual está construido como SaaS modular con sidebar y páginas separadas (/admin, /groups, /members, /interviews). **Esto viola la arquitectura de interacción del PRD v2 (sección 7).**

**Acción:** Eliminar todo el contenido de `frontend/` y reconstruir desde cero con:

- Next.js 14+ (App Router)
- React 18+
- TypeScript
- TailwindCSS
- React Flow (para el canvas organizacional)
- Dependencias UI: lucide-react (iconos), shadcn/ui (componentes base)

### 🗑️ Eliminado

- `agents/` — Eliminado. Ya no aplica.
- `docs/ARCHITECTURE_V1_FINAL.md` — Eliminado. PRD v2 es la única fuente de verdad.

---

## 3. Arquitectura de interacción (CRÍTICO — lee esto)

El PRD v2 sección 7 define reglas que son **no negociables** para el frontend:

### Reglas fundamentales

1. **El canvas organizacional es la pantalla principal.** No es un módulo. Es la home del usuario premium.
2. **El usuario nunca pierde el contexto del canvas.** Toda funcionalidad se abre como panel lateral, overlay o capa. Nunca como navegación a otra página.
3. **3 capas sobre el mismo canvas:** Estructura+Captura → Análisis → Resultados. Cambiar de capa no cambia de pantalla. *(La antigua capa "Recolección" se fusionó en "Estructura+Captura" por decisión del 21 de abril de 2026 — ver `docs/MODEL_PHILOSOPHY.md`.)*
4. **Panel lateral contextual derecho:** se abre al hacer clic en un nodo. Su contenido cambia según la capa activa.
5. **Sidebar mínimo izquierdo (colapsable):** solo para settings, billing, documentos, selector de org, cuenta.
6. **Diagnóstico narrativo:** panel expandido lateral derecho (60-70% viewport), canvas visible en segundo plano.

### Comportamiento por capa (fuente de verdad)

**CAPA ESTRUCTURA+CAPTURA:** *(unificada — antes eran dos capas separadas)*
- El admin construye el mapa organizacional, caracteriza cada nodo y gestiona las invitaciones desde la misma vista.
- Cada nodo tiene: nombre, tipo (`unit` | `person`), posición jerárquica vía `parent_node_id`, área, contexto libre, descripción. Para nodos `person`: email del respondiente y `role_label` del estado de campaña activa.
- El email se ingresa **UNA SOLA VEZ** en el panel lateral del nodo `person` — es la persona que responderá la entrevista.
- También desde esta capa el admin puede subir documentos institucionales (estatutos, misión, manuales) que alimentarán el análisis de IA. Los documentos pueden ser permanentes (transversales a campañas) o asociados a la campaña activa.
- El panel lateral en esta capa muestra pestañas contextuales:
  - **Identidad** — formulario de edición del nodo (nombre, tipo, padre jerárquico, descripción).
  - **Estado de campaña** — email asignado, `role_label`, `context_notes`, estado de la entrevista (sin invitar / invitado / en progreso / completado / vencido), link copiable, botón WhatsApp, fecha de respuesta.
  - **Documentos** — adjuntos al nodo si aplica.
- Los nodos `person` sin email asignado muestran un aviso "Asigna un email en este panel para invitar".
- Ver `docs/MODEL_PHILOSOPHY.md` §7 para la convención visual completa.

**CAPA ANÁLISIS:**
- Objetivo: comprensión rápida y situada del estado de la organización.
- Canvas con nodos coloreados por nivel de tensión (verde ≥ 3.8 / amarillo 2.5–3.8 / rojo < 2.5).
- Filtros por dimensión: al activar una dimensión → canvas actualiza colores para reflejar solo esa dimensión.
- Panel lateral (clic en nodo): score por dimensión, comparación con promedio org, resumen de percepciones agregadas.
- Coordinación visual obligatoria: al filtrar una dimensión → canvas resalta nodos afectados; al cerrar panel → canvas vuelve a vista general.
- Navegación: clic en nodo → análisis contextual de ese nodo; "Ver hallazgos relacionados" → navega a Capa Resultados.

**CAPA RESULTADOS:**
- Objetivo: exploración de hallazgos y recomendaciones.
- Nodos con badges de insights (íconos que indican cuántos hallazgos están asociados al nodo).
- Panel lateral (clic en nodo): hallazgos del nodo con score de confianza, recomendaciones asociadas.
- Navegación bidireccional obligatoria: clic en nodo → panel con hallazgos; clic en hallazgo → canvas resalta nodos relevantes.
- Panel narrativo expandido (60–70% viewport) con canvas visible y reactivo en segundo plano.
- Modo lectura ampliado disponible para gráficas complejas; siempre con botón "Volver al canvas".
- Ver `docs/ARQUITECTURA_ANALISIS_RESULTADOS.md` para especificación completa.

### Antipatrones prohibidos

- ❌ Sidebar con secciones "Grupos", "Miembros", "Entrevistas", "Resultados"
- ❌ Páginas separadas para gestión de entrevistas o resultados
- ❌ Dashboard genérico post-login
- ❌ Rutas tipo /admin/members, /admin/interviews, /admin/results, /analysis, /dashboard
- ❌ Settings, billing o documentos como páginas full-screen
- ❌ Reportes o hallazgos sin contexto estructural (toda información debe ser trazable a nodo(s) específicos)
- ❌ Narrativa separada del canvas (el panel narrativo siempre tiene el canvas visible detrás)
- ❌ Canvas decorativo en capas Análisis/Resultados (si el canvas no reacciona al contenido del panel, algo está mal)

### Estructura de rutas permitida

```
/login                          — autenticación
/orgs                           — selector de org (si tiene múltiples)
/org/{org_id}/canvas            — canvas principal (home premium)
/org/{org_id}/settings          — settings (abre como panel sobre canvas)
/org/{org_id}/billing           — billing (abre como panel sobre canvas)
/org/{org_id}/documents         — documentos (abre como panel sobre canvas)
/org/{org_id}/score             — score radar (home free)
/interview/{token}              — experiencia del entrevistado (flujo independiente)
/account                        — settings de cuenta
```

---

## 4. Modelo de negocio (Freemium)

### Plan Free — Diagnóstico rápido (SIN autenticación)

- Cualquier persona accede a `/onboarding` sin crear cuenta.
- Completa: info org → encuesta líder (4 dimensiones) → agregar miembros (emails).
- Se crea `QuickAssessment` sin `user_id` (anónimo).
- Redirige a `/score/{id}` con resultado.
- Los miembros responden en `/interview/[token]` (público).
- CTA en score: "Crea tu cuenta para el diagnóstico completo".
- **No tiene canvas, no tiene IA, no tiene diagnóstico narrativo.**

### Plan Premium — Producto completo (CON autenticación)

- Canvas organizacional con 4 capas.
- 8 dimensiones: Liderazgo, Comunicación, Cultura, Procesos, Poder, Economía/Finanzas, Operación, Misión.
- Entrevistas profundas (Likert + abiertas + selección múltiple).
- Motor IA híbrido (scoring + LLM + análisis de redes).
- Diagnóstico narrativo con hallazgos y recomendaciones.

---

## 5. Flujos de Usuario

### Free (Encuesta Rápida) — SIN autenticación

1. Landing `/` → CTA "Diagnostica tu organización gratis" → `/onboarding`
2. `/onboarding`: info org → encuesta líder → agregar miembros (emails)
3. Se crea `QuickAssessment` sin `user_id` (anónimo)
4. Redirige a `/score/{id}` con resultado
5. Miembros responden en `/interview/[token]` (público, sin auth)
6. CTA en score: "Crea tu cuenta para el diagnóstico completo" → `/register`

### Premium (Canvas) — CON autenticación

1. `/register` → crea cuenta → `/org/{uuid}/canvas`
2. `/login` → si tiene org → `/org/{uuid}/canvas` directo
3. Canvas requiere auth (`useAuth` hook)
4. Al crear cuenta desde score page, vincular el `QuickAssessment` existente (futuro)

### Landing Page (`/`)

- CTA primario: "Diagnostica tu organización gratis" → `/onboarding`
- CTA secundario: "Iniciar sesión" → `/login`
- No requiere autenticación

---

## 6. Modelo de datos

> **Fuente de verdad del modelo estructural:** `docs/MODEL_PHILOSOPHY.md`.
> Esta sección es un resumen de las decisiones que gobiernan el refactor Node + Edge del Sprint 1. En caso de conflicto con MODEL_PHILOSOPHY.md, ese documento gana (y a su vez cede ante el PRD v2.1).

### Refactor Node + Edge (decisión del 21 de abril de 2026)

El modelo estructural se unifica. Las tablas separadas `groups` y `members` se colapsan en una única tabla `nodes` con un campo discriminador `type`:

- `Group` → `Node { type = "unit" }`.
- `Member` → `Node { type = "person" }`.
- `LateralRelation` → `Edge` con enum cerrado `edge_type ∈ { "lateral", "process" }`. **No existe el valor `"otro"`.** No existe `"hierarchical"` (la jerarquía vive en `parent_node_id`).

### Modelos existentes que necesitan ajustes

**User** — Agregar:
- `auth_provider: str` (default "email", futuro: "google", "microsoft")
- Eliminar relación directa `organization_id` → reemplazar con tabla Membership

**Organization** — Agregar:
- `type: str` (empresa, ong, equipo, otro)
- `size_range: str` (1-10, 11-50, 51-200, 200+)
- `plan: str` (free, premium)
- Eliminar `admin_id` → reemplazar con Membership

**Interview** — Agregar:
- `dimension: str` (para asociar respuestas a dimensión)
- `campaign_id: UUID` (FK a `assessment_campaigns`)
- Revisar `schema_version`

### Modelos nuevos del refactor

```python
# Node — reemplaza Group y Member. Identidad permanente.
class Node:
    id: UUID
    organization_id: UUID
    parent_node_id: UUID | None
    type: str              # "unit" | "person"
    name: str
    position_x: float
    position_y: float
    created_at: datetime
    # Invariantes clave (ver MODEL_PHILOSOPHY.md §8):
    #  - person requiere parent_node_id no nulo y el padre es type=unit
    #  - unit puede tener parent nulo (raíz) o apuntar a otro unit
    #  - la relación parent_node_id es acíclica

# Edge — reemplaza LateralRelation. Relación funcional horizontal entre units.
class Edge:
    id: UUID
    organization_id: UUID
    source_node_id: UUID   # debe ser type=unit
    target_node_id: UUID   # debe ser type=unit
    edge_type: str         # enum cerrado: "lateral" | "process"
    created_at: datetime
    # Invariantes: no self-loop, no duplicado (source, target, edge_type),
    # no edges que toquen persons, no edges "hierarchical".

# NodeState — estado por campaña. Lo que cambia entre diagnósticos.
class NodeState:
    id: UUID
    node_id: UUID
    campaign_id: UUID
    email_assigned: str | None    # solo persons
    role_label: str
    context_notes: str | None
    interview_token: str | None   # regenerado por campaña
    interview_status: str         # pending | in_progress | completed | expired
    invited_at: datetime | None
    completed_at: datetime | None
    # UNIQUE (node_id, campaign_id)

# AssessmentCampaign — longitudinalidad de primera clase.
class AssessmentCampaign:
    id: UUID
    organization_id: UUID
    name: str                     # ej. "Diagnóstico Inicial"
    status: str                   # draft | active | closed
    started_at: datetime
    closed_at: datetime | None
    created_by_user_id: UUID
    # A lo sumo UNA campaign active por organization simultáneamente.
    # Schema existe desde Sprint 1; UI de múltiples campañas hasta Sprint 3.

# Membership — reemplaza relación directa User-Organization.
class Membership:
    user_id: UUID
    org_id: UUID
    role: str  # owner, admin, viewer

# QuickAssessment (plan free — sin cambios respecto al modelo previo)
class QuickAssessment:
    org_id: UUID
    leader_responses: dict
    member_count: int
    scores: dict
    created_at: datetime

# Finding y Recommendation — definidos en docs/MOTOR_ANALISIS.md §2.
# NO se modifican en este sprint. Sus FKs a groups.id siguen siendo válidos
# porque la migración preserva UUIDs. Ver MODEL_PHILOSOPHY.md §9 para deuda.
```

### Coexistencia con el motor de análisis

Las tablas del motor (`analysis_runs`, `node_analyses`, `group_analyses`, `org_analyses`, `findings`, `recommendations`, `evidence_links`, `document_extractions`) **no se modifican** en este refactor. La migración conserva UUIDs al crear `nodes`, así que `node_analyses.group_id` y `group_analyses.group_id` siguen resolviéndose contra los UUIDs preservados. Ver `docs/MODEL_PHILOSOPHY.md` §9 y `docs/DEUDA_DOCUMENTAL.md` para la deuda técnica conocida.

---

## 7. Banco de preguntas — Migración

El banco actual (`backend/app/questions.py`) usa 5 lentes: actores, procesos, reglas, incentivos, episodios.

El PRD v2 define **8 dimensiones** para premium y **4 dimensiones** para free.

### Mapeo de migración

| Lente actual | → Dimensión PRD v2 |
|---|---|
| actores | Liderazgo + Poder |
| procesos | Procesos + Operación |
| reglas | Cultura + Procesos |
| incentivos | Economía/Finanzas + Cultura |
| episodios | Transversal (se redistribuye) |

**Acción:** Reestructurar `questions.py` para que cada pregunta tenga un campo `dimension` alineado con las 8 dimensiones del PRD. Crear un segundo banco `questions_free.py` con 1-2 preguntas Likert por dimensión para las 4 dimensiones free.

---

## 8. Roadmap de ejecución (sprints)

### Fase 0 — Free MVP (prioridad máxima)

**Objetivo:** Validar que los líderes completan el flujo free y que la tasa de respuesta de miembros es viable.

**Backend:**
- [ ] Modelo QuickAssessment
- [ ] Endpoint POST /api/quick-assessment (crear evaluación rápida)
- [ ] Endpoint POST /api/quick-assessment/{id}/invite (invitar miembros)
- [ ] Endpoint POST /api/quick-assessment/{id}/respond (respuesta de miembro)
- [ ] Endpoint GET /api/quick-assessment/{id}/score (obtener score radar)
- [ ] Motor de scoring simple (promedio por dimensión)
- [ ] Banco de preguntas free (4 dimensiones)

**Frontend:**
- [ ] Setup nuevo frontend: Next.js + TailwindCSS + TypeScript
- [ ] Página de registro
- [ ] Flujo de onboarding free (bienvenida → encuesta líder → ingreso miembros)
- [ ] Experiencia de encuesta para miembros invitados (mobile-first)
- [ ] Pantalla de espera con progreso en tiempo real
- [ ] Pantalla de score radar con CTA upgrade

### Fase 1 — Canvas y estructura

**Backend:** *(refactor Node+Edge — ver `docs/MODEL_PHILOSOPHY.md`)*
- [ ] Crear modelo unificado `Node` (absorbe `Group` como `type=unit` y `Member` como `type=person`) con posiciones x,y en canvas
- [ ] Crear modelo `Edge` (reemplaza `LateralRelation`) con `edge_type ∈ {lateral, process}`
- [ ] Crear modelo `NodeState` (estado por campaña: email, role_label, context_notes, interview_status/token)
- [ ] Crear modelo `AssessmentCampaign` (schema Sprint 1, UI de múltiples campañas hasta Sprint 3)
- [ ] Modelo Membership
- [ ] Endpoints CRUD de nodos con posición
- [ ] Endpoint de importación CSV
- [ ] Endpoint de templates prediseñados

**Frontend:**
- [ ] Integrar React Flow
- [ ] Canvas con Capa Estructura
- [ ] Panel lateral contextual (estado Estructura)
- [ ] Sidebar mínimo
- [ ] Estado 0 del canvas (primer uso — ver PRD v2 sección 8.3)
- [ ] Templates prediseñados
- [ ] Importación CSV con wizard
- [ ] Tooltips progresivos de onboarding

### Fase 2 — Recolección

**Backend:**
- [ ] Sistema de invitaciones con tokens (ya existe parcialmente, extender)
- [ ] Banco de preguntas premium (8 dimensiones)
- [ ] Endpoints de gestión de entrevistas (recordatorios, revocación)
- [ ] Cálculo de umbral (40%, mínimo 5)

**Frontend:**
- [ ] Capa Recolección del canvas
- [ ] Panel lateral en estado Recolección
- [ ] Experiencia del entrevistado premium (responsive, guardado automático)
- [ ] Indicadores de estado en nodos

### Fase 3 — Motor de IA

**Backend:**
- [ ] Pipeline de scoring cuantitativo completo
- [ ] Integración con Claude API para análisis NLP
- [ ] Análisis de red (métricas de grafo)
- [ ] Síntesis cruzada
- [ ] Scores de confianza
- [ ] Generación de hallazgos y recomendaciones

### Fase 4 — Resultados

**Frontend:**
- [ ] Capa Análisis del canvas (mapa de calor)
- [ ] Capa Resultados del canvas
- [ ] Panel lateral en estados Análisis y Resultados
- [ ] Panel expandido de diagnóstico narrativo (60-70% viewport)
- [ ] Dashboard de scores (radar chart)
- [ ] Exportación PDF/DOCX

### Fase 5 — Producto completo

- [ ] Carga de documentos + RAG
- [ ] Comparación temporal
- [ ] Roles viewer y admin colaborador
- [ ] Zoom semántico
- [ ] Relaciones laterales visuales

---

## 9. Convenciones de código

### Backend (Python)

- FastAPI + SQLModel + PostgreSQL
- Migraciones con Alembic (siempre generar migración al cambiar modelos)
- Nombres de tablas en plural snake_case: `organizations`, `members`
- UUIDs como primary keys
- Soft delete con `deleted_at` donde aplique
- Validación con Pydantic/SQLModel schemas
- Tests con pytest + httpx

### Frontend (TypeScript)

- Next.js 14+ con App Router
- React 18+ con hooks
- TailwindCSS para estilos (no CSS modules, no styled-components)
- React Flow para el canvas
- Componentes en PascalCase: `CanvasLayer.tsx`
- Hooks custom en `hooks/`: `useCanvas.ts`, `usePanel.ts`
- API client en `lib/api.ts`
- Types en `types/`: `organization.ts`, `node.ts`, `interview.ts`

### General

- Commits en español, descriptivos: "feat: agregar capa Recolección al canvas"
- No dejar console.log en producción
- Variables de entorno en .env (nunca hardcoded)
- Docker Compose para desarrollo local

---

## 10. Cómo ejecutar

```bash
# Clonar y entrar
cd laboratorio_v5

# Copiar env
cp .env.example .env

# Levantar servicios
docker-compose up --build

# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# Health check: http://localhost:8000/health
```

---

## 11. Reglas para Claude Code

1. **Siempre lee el PRD v2.1 antes de tomar decisiones de producto.** Si no estás seguro de cómo debe funcionar algo, búscalo ahí.
2. **No construyas nada que viole la sección 7 del PRD v2.1 (arquitectura de interacción).** Si una feature requiere navegar fuera del canvas, rediseña hasta que pueda vivir como panel, overlay o capa.
3. **Ejecuta una fase a la vez.** No saltes a Fase 2 sin terminar Fase 0 y 1.
4. **Siempre genera migraciones Alembic al modificar modelos.**
5. **Siempre verifica que el frontend compile sin errores antes de hacer commit.**
6. **Conserva el backend existente.** Extiende, no reescribas.
7. **El frontend se reconstruye desde cero.** No intentes adaptar el código actual.
8. **Pregunta antes de asumir** si algo no está claro en el PRD.

---

## 12. Motor de Análisis

El motor de análisis es el pipeline que convierte respuestas de entrevistas + documentos + estructura organizacional en hallazgos, recomendaciones y narrativa. Se ejecuta externamente (Codex/LLM API) y entrega resultados al backend via `POST /organizations/{org_id}/diagnosis`.

### Pipeline de 4 pasos (NO negociable)

El motor **nunca envía datos crudos al LLM**. Siempre construye representaciones intermedias primero.

**PASO 1 — Extracción por nodo** (un prompt por persona/nodo)
- Input: respuestas cuantitativas + texto libre + rol + nivel jerárquico + context_notes del admin + documentos del nodo si los hay
- Output: `node_analysis` (objeto estructurado, NO narrativa)
- Guardado en: tabla `node_analyses`

**PASO 2 — Síntesis por grupo** (un prompt por grupo)
- Input: todos los `node_analyses` del grupo + scores cuantitativos + notas del admin + documentos del grupo
- Output: `group_analysis` con patrones internos identificados
- Guardado en: tabla `group_analyses`

**PASO 3 — Análisis organizacional** (un prompt)
- Input: todos los `group_analyses` + estructura del organigrama + métricas de red + documentos institucionales ya procesados
- Output: `org_analysis` con patrones transversales y contradicciones
- Guardado en: tabla `org_analyses`

**PASO 4 — Síntesis ejecutiva** (un prompt)
- Input: outputs de pasos 2 y 3 (ya estructurados, **NO datos crudos**)
- Output: `findings` + `recommendations` + `narrative_md`
- **Regla:** el LLM NO puede introducir hallazgos que no vengan de pasos anteriores

### Tablas del motor

```
analysis_runs, node_analyses, group_analyses, org_analyses,
document_extractions, findings, recommendations, evidence_links
```

### Regla de oro

> Si un prompt del motor recibe datos crudos de entrevistas sin transformación previa, hay un **bug de arquitectura**.

## Ejecución de tests

Los tests usan testcontainers con Postgres real (no SQLite).
Por esa razón deben ejecutarse desde el host, no desde dentro
del contenedor backend:

  cd backend && uv run pytest tests

El comando `docker compose exec backend uv run pytest` falla
porque testcontainers necesita acceso al Docker daemon del
host. El runner de CI debe correr `uv` directamente en el
ambiente del worker, con acceso a Docker.
