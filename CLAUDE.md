# CLAUDE.md — Laboratorio de Modelamiento Institucional con IA

> **Este archivo es la guía principal para Claude Code.**
> Léelo completo antes de ejecutar cualquier tarea.

---

## 1. Qué es este proyecto

Una plataforma web que permite a líderes organizacionales (CEOs, directores, gerentes de ONG) diagnosticar cómo funciona su organización internamente, combinando estructura organizacional + entrevistas a miembros + análisis con IA.

**Fuente de verdad:** `docs/PRD_v2_Diagnostico_Organizacional.docx` — este PRD gobierna todas las decisiones. Si hay conflicto entre este archivo, el código existente o cualquier otro documento, el PRD v2 gana.

**Documento secundario (referencia técnica):** Eliminado (`docs/ARCHITECTURE_V1_FINAL.md`). El PRD v2 es la única fuente de verdad.

---

## 2. Estado actual del repositorio

### ✅ Conservar (backend)

El backend tiene una base funcional que debe mantenerse y extenderse:

- **Stack:** FastAPI + SQLModel + PostgreSQL + Alembic (migraciones) + Docker
- **Auth:** JWT con access + refresh token. Login, logout, /me. Funciona.
- **Modelos existentes:** User, Organization, Group, Member, Interview, AnalysisJob. Necesitan ajustes (ver sección 5) pero la estructura es sólida.
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
3. **4 capas sobre el mismo canvas:** Estructura → Recolección → Análisis → Resultados. Cambiar de capa no cambia de pantalla.
4. **Panel lateral contextual derecho:** se abre al hacer clic en un nodo. Su contenido cambia según la capa activa.
5. **Sidebar mínimo izquierdo (colapsable):** solo para settings, billing, documentos, selector de org, cuenta.
6. **Diagnóstico narrativo:** panel expandido lateral derecho (60-70% viewport), canvas visible en segundo plano.

### Antipatrones prohibidos

- ❌ Sidebar con secciones "Grupos", "Miembros", "Entrevistas", "Resultados"
- ❌ Páginas separadas para gestión de entrevistas o resultados
- ❌ Dashboard genérico post-login
- ❌ Rutas tipo /admin/members, /admin/interviews, /admin/results
- ❌ Settings, billing o documentos como páginas full-screen

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

### Modelos existentes que necesitan ajustes

**User** — Agregar:
- `auth_provider: str` (default "email", futuro: "google", "microsoft")
- Eliminar relación directa `organization_id` → reemplazar con tabla Membership

**Organization** — Agregar:
- `type: str` (empresa, ong, equipo, otro)
- `size_range: str` (1-10, 11-50, 51-200, 200+)
- `unit_type: str` (persona, grupo)
- `plan: str` (free, premium)
- Eliminar `admin_id` → reemplazar con Membership

**Group** → Renombrar conceptualmente a **Node** en el PRD, pero puede mantenerse como `Group` en DB si se agregan:
- `area: str`
- `level: int` (nivel jerárquico)
- `position_x: float, position_y: float` (posición en canvas)

**Member** — Sin cambios mayores. Revisar que `token_status` incluya todos los estados del PRD.

**Interview** — Agregar:
- `dimension: str` (para asociar respuestas a dimensión)
- Revisar `schema_version`

### Modelos nuevos requeridos

```python
# Membership (reemplaza relación directa User-Organization)
class Membership:
    user_id: UUID
    org_id: UUID
    role: str  # owner, admin, viewer

# LateralRelation
class LateralRelation:
    source_node_id: UUID
    target_node_id: UUID
    type: str  # colaboración, dependencia, otro

# QuickAssessment (plan free)
class QuickAssessment:
    org_id: UUID
    leader_responses: dict  # JSON con respuestas del líder
    member_count: int
    scores: dict  # JSON con scores por dimensión
    created_at: datetime

# Finding
class Finding:
    diagnostic_id: UUID
    dimension: str
    title: str
    description: str
    confidence: str  # high, medium, low
    sources: list  # JSON

# Recommendation
class Recommendation:
    diagnostic_id: UUID
    priority: int
    title: str
    description: str
    justification: str
```

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

**Backend:**
- [ ] Migrar modelo Group para soportar posiciones x,y (canvas)
- [ ] Modelo LateralRelation
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

1. **Siempre lee el PRD v2 antes de tomar decisiones de producto.** Si no estás seguro de cómo debe funcionar algo, búscalo ahí.
2. **No construyas nada que viole la sección 7 del PRD (arquitectura de interacción).** Si una feature requiere navegar fuera del canvas, rediseña hasta que pueda vivir como panel, overlay o capa.
3. **Ejecuta una fase a la vez.** No saltes a Fase 2 sin terminar Fase 0 y 1.
4. **Siempre genera migraciones Alembic al modificar modelos.**
5. **Siempre verifica que el frontend compile sin errores antes de hacer commit.**
6. **Conserva el backend existente.** Extiende, no reescribas.
7. **El frontend se reconstruye desde cero.** No intentes adaptar el código actual.
8. **Pregunta antes de asumir** si algo no está claro en el PRD.
