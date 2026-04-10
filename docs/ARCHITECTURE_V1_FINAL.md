# ARCHITECTURE_V1_FINAL — Laboratorio de Modelamiento Institucional con IA

> **Estado:** Fuente única de verdad. Lista para construcción agéntica.  
> **Versión:** 1.0 FINAL — Abril 2026  
> **Regla:** Todo lo que no está aquí no existe. Cualquier ambigüedad no resuelta debe elevarse antes de codificar.  
> **Jerarquía de fuentes:** Este documento (fuente principal) > Documento V1 (cobertura complementaria)

---

## Índice

1. [Principios del producto](#1-principios-del-producto)
2. [Problemas críticos detectados](#2-problemas-críticos-detectados)
3. [Flujo de usuario](#3-flujo-de-usuario)
4. [Modelo de datos](#4-modelo-de-datos)
5. [API — Contratos completos](#5-api--contratos-completos)
6. [Reglas de negocio](#6-reglas-de-negocio)
7. [Estados del sistema](#7-estados-del-sistema)
8. [Eventos y procesos sync + async](#8-eventos-y-procesos-sync--async)
9. [Pipeline de análisis](#9-pipeline-de-análisis)
10. [Output del sistema — Reportes](#10-output-del-sistema--reportes)
11. [Banco de preguntas](#11-banco-de-preguntas)
12. [Decisiones de producto](#12-decisiones-de-producto)
13. [Riesgos de construcción agéntica](#13-riesgos-de-construcción-agéntica)
14. [Checklist de verificación](#14-checklist-de-verificación)

---

## 1. Principios del producto

Estos principios gobiernan cada decisión de diseño. Cuando haya conflicto entre funcionalidad y principio, el principio gana.

**P1 — La brecha formal/real es el producto**  
El valor no está en capturar datos, sino en revelar la distancia entre lo que la organización dice ser y lo que efectivamente hace. Cada pieza de UX debe facilitar esa revelación.

**P2 — El admin construye; el sistema analiza**  
El admin carga contexto y estructura. La IA produce el diagnóstico. Nunca invertir ese rol: el admin no debe sentir que él hace el análisis.

**P3 — Los reportes A y B son inseparables**  
El Informe A (ciego) y el Informe B (orientado) no son dos outputs opcionales. Son un sistema. La divergencia entre ambos es diagnóstica en sí misma.

**P4 — Primero valor, luego completitud**  
Un diagnóstico parcial con datos reales vale más que un formulario completo vacío. El sistema debe producir valor incremental con cada dato nuevo.

**P5 — Confidencialidad estructural**  
Las respuestas individuales de entrevistados nunca se atribuyen nominalmente en los reportes. El sistema hace cumplir esto técnicamente, no solo por política.

**P6 — El contexto del admin es dato analítico**  
Las notas del admin sobre miembros y grupos entran al análisis con el mismo peso que las entrevistas. No son metadatos decorativos.

---

## 2. Problemas críticos detectados

### P1 — Ambigüedades bloqueantes (resueltas)

**PC-01 — Condición del botón "Generar diagnóstico"**  
El boceto mostraba el botón sin requerir `StrategicContext`. El V1 lo requería para Informe B.  
**Resolución:** El botón se habilita sin `StrategicContext` y genera solo Informe A. Si existe `StrategicContext`, genera además Informe B. Ver R1-R5 en sección 6.

**PC-02 — Índices de DB no especificados**  
El V1 mencionaba campos desnormalizados sin definir índices.  
**Resolución:** Índices explícitos en sección 4.2.

**PC-03 — POST /auth/register creaba organización "opcional"**  
"Opcional" no es un estado válido para el sistema.  
**Resolución:** Register siempre crea `User` con `org_id=null`. El primer login detecta ausencia de org y fuerza onboarding.

**PC-04 — Sin versionado del schema de preguntas**  
Si el schema cambia entre versiones, los datos históricos se vuelven inconsistentes.  
**Resolución:** Campo `question_schema_version` (VARCHAR 20, default `'v1.0'`) en `Interview`.

**PC-05 — Mecanismo de agregación de respuestas no especificado**  
Sin especificación, el agente implementa concatenación directa → prompts de 200k tokens.  
**Resolución:** Pre-aggregation con LLM ligero (`gpt-4o-mini`) antes del prompt principal. Ver Fase F3 en sección 9.

### P2 — Riesgos de producto (resueltos)

**PR-01 — Cálculo del 60% ambiguo**  
El denominador excluye miembros con `token_status=expired` al momento de triggerear.  
Fórmula exacta en R5, sección 6.1.

**PR-02 — DELETE hard eliminaba entrevistas completadas**  
**Resolución:** Soft delete en `Member` y `Group`. Campo `deleted_at`. Ver sección 4.1.

**PR-03 — Output del LLM truncado se guardaba como válido**  
**Resolución:** Fase F8 de verificación estructural. Ver sección 9.

**PR-04 — Sin retry para AnalysisJob fallido**  
**Resolución:** Botón "Reintentar" crea nuevo job con `retry_of_job_id`. Ver sección 5.7.

### P3 — Deuda técnica aceptada en V1

- **PT-01:** Schema de preguntas en código, no en DB. Imposibilita A/B testing. Aceptado.
- **PT-02:** Un solo admin por organización. `role=viewer` en schema, no implementado.
- **PT-03:** Sin queue distribuida. Worker síncrono con timeout 10 min. Límite ~50 orgs concurrentes.
- **PT-04:** Adjuntos de miembros en `Interview.attachments` JSONB en lugar de tabla `Document` normalizada.

### P4 — Nota crítica de infraestructura (migración DB)

`alembic upgrade head` **debe ejecutarse en el entrypoint del contenedor** antes de que FastAPI acepte requests. No implementar como script manual. Sin esto, la tabla `users` no existe en PostgreSQL y el login falla en el primer deploy.

---

## 3. Flujo de usuario

Dos actores: **Admin** (compra y configura) y **Miembro** (responde entrevista). Flujos independientes que convergen en el análisis.

### 3.1 Flujo del Admin

#### PASO 0 — Autenticación

| Elemento | Especificación |
|----------|---------------|
| Entrada | Email + password. Sin OAuth en V1. |
| Validación client | Email válido (regex). Password no vacío. Botón deshabilitado durante request. |
| Acción OK | Verificar hash bcrypt. Emitir JWT (payload: `user_id`, `org_id\|null`, `role`). Guardar en httpOnly cookie + localStorage para refresh. Redirigir: si `org_id=null` → `/onboarding`. Si `org_id` existe → `/home`. |
| Acción FAIL | HTTP 401. Mensaje: "Email o contraseña incorrectos." (no revelar cuál falla). Bloquear cuenta 5 min después de 5 intentos fallidos. |
| Registro nuevo | POST `/auth/register`: crea `User` con `org_id=null`. Redirige a `/onboarding`. NO crear organización en este paso. |

Sesión: JWT expira 7 días. Refresh silencioso si request ocurre con <24h de expiración. Logout invalida token server-side (tabla `token_blacklist`).

#### PASO 1 — Onboarding (creación de organización)

| Elemento | Especificación |
|----------|---------------|
| Condición entrada | `user.org_id = null`. Forzado: no se puede saltar ni navegar a otra ruta. |
| Campos obligatorios | `name` (max 120), `mission` (max 500). Bloquear submit hasta que ambos tengan contenido. |
| Campos opcionales V1 | `description`, `ways_of_working`, `sector`. Mostrar como "mejora el análisis" pero no bloquear. |
| Acción OK | INSERT Organization. INSERT UserOrganization. UPDATE User SET org_id. Emitir nuevo JWT con org_id. Redirigir a `/home`. |
| Edge case | Si el usuario recarga durante onboarding: detectar `org_id=null` y volver a `/onboarding`. No crear organización duplicada. |
| Restricción | Un usuario puede pertenecer a una sola organización en V1. No mostrar opción de "unirse a org existente". |

#### PASO 2 — Home (dashboard central)

| Elemento | Especificación |
|----------|---------------|
| Carga inicial | GET `/organizations/:id/dashboard`. Retorna: `{groups[], completeness{groups_with_info_pct, members_created_pct, interviews_completed_pct}, pending_interviews[], latest_job_status}`. |
| Panel completitud | Tres barras de progreso. Tooltip explica qué falta para cada métrica. Si todas al 100%: destacar visualmente el botón "Generar diagnóstico". |
| Lista grupos | Árbol colapsable. Cada nodo: nombre, N miembros, N entrevistas completadas / N total. Clic → abre panel lateral de edición (no navega). |
| Botón Generar | Deshabilitado hasta cumplir R1-R5. Cuando deshabilitado: hover muestra tooltip con condiciones faltantes específicas. |
| Sin grupos | Estado vacío con CTA: "Crea tu primer grupo para comenzar". |

#### PASO 3 — Gestión de grupos

| Elemento | Especificación |
|----------|---------------|
| Crear grupo | Modal. Campos: `name*`, `description`, `parent_group_id` (select de grupos existentes), `admin_notes`. POST `/organizations/:id/groups`. Cerrar modal → actualizar lista en Home sin reload. |
| Profundidad máx | 3 niveles (depth 0, 1, 2). Si el grupo padre ya es depth=2: no mostrar en select. Error 422 si se intenta crear depth=3 via API. |
| Editar grupo | Mismo modal reutilizado. PATCH. Todos los campos editables menos `parent_group_id` (cambiar jerarquía es V2). |
| Eliminar grupo | Solo si: no tiene miembros Y no tiene subgrupos. Confirmar con nombre del grupo escrito. DELETE retorna 409 si tiene dependencias. |
| Adjuntos | Upload inline en modal de edición. Máx 5 archivos, 10 MB total por grupo. Tipos: pdf, jpg, png. Almacenar en S3. Registro en tabla `Document`. |
| Efecto análisis | `name`, `description`, `admin_notes` entran al análisis. Documentos se procesan en Fase F4 del pipeline. |

#### PASO 4 — Gestión de miembros

| Elemento | Especificación |
|----------|---------------|
| Crear miembro | Modal desde Home o desde vista de grupo. Campos: `name*`, `email*`, `group_id*` (select), `role_description*`, `admin_notes`. |
| Al guardar | 1. INSERT Member. 2. Generar `interview_token` = UUID v4 en texto plano (guardar hash SHA-256 en DB, **no el token**). 3. SET `token_status=pending`, `token_expires_at=now()+14 days`. 4. Encolar email async. 5. Retornar member con `token_status`. |
| Email al miembro | Enviado async (no bloquea el response). Si falla: `token_status` permanece pending, log de error, admin ve indicador "email no enviado" con botón reenviar. |
| Reenviar invitación | POST `/members/:id/resend-invite`. Si `token_status=completed`: 409 "Entrevista ya completada". Si pending/in_progress/expired: regenerar token, actualizar `token_sent_at` y `token_expires_at`. Si era expired: resetear a pending. |
| Eliminar miembro | Soft delete: SET `deleted_at=now()`. Si tenía Interview completada: conservar Interview para análisis. Si Interview en progreso: marcar `Interview.status=abandoned`. |
| Restricción email | UNIQUE(`org_id`, `email`). Si email ya existe en la org: 409 "Este email ya tiene una invitación en esta organización". |

#### PASO 5 — Input estratégico

| Elemento | Especificación |
|----------|---------------|
| Cuándo aparece | Siempre visible en Home como sección colapsable. No bloquea ningún otro paso. |
| Campos obligatorios para B | `objectives` (TEXT NOT NULL), `concerns` (TEXT NOT NULL). |
| Campos opcionales | `key_questions`, `additional_context`. |
| Comportamiento save | Auto-save con debounce 2s. Última versión guardada = la que usa el análisis. |
| Edición post-análisis | Se puede editar siempre. Cada análisis captura snapshot inmutable en `input_snapshot`. |
| Sin StrategicContext | El sistema genera solo Informe A. Aviso visible: "Sin contexto estratégico, no se generará el Informe B." No es un error; es un estado válido. |

#### PASO 6 — Generación y vista de reportes

| Elemento | Especificación |
|----------|---------------|
| Trigger | POST `/organizations/:id/analysis/trigger`. Backend valida R1-R5, crea `AnalysisJob` A + (si hay `StrategicContext`) `AnalysisJob` B. Ambos `status=queued`. |
| Polling | Frontend hace polling GET `/analysis/latest` cada 10s mientras algún job esté en `queued\|processing`. Timeout UI: 15 min. Si supera: "Tomando más tiempo del esperado. Puedes cerrar esta pantalla; te notificaremos." |
| Vista reportes | Tabs: Informe A \| Informe B (si existe). Texto renderizado con markdown básico. Botón "Descargar PDF" genera PDF del `result_text` server-side. |
| Rediagnóstico | Permitido siempre. Cada trigger crea nuevo par de jobs. GET `/analysis/jobs` muestra historial completo. GET `/analysis/latest` devuelve el par más reciente completado. |
| Análisis en progreso | Si ya hay un job `queued\|processing` para esta org: botón cambia a "Análisis en curso". No se puede triggerear otro hasta que termine o falle. |

### 3.2 Flujo del Miembro (entrevistado)

El miembro accede con un token único. No crea cuenta. No necesita contraseña.

| Paso | Especificación ejecutable |
|------|--------------------------|
| Entrada por token | GET `/interviews/:token`. Sistema: 1. Hash SHA-256 del token recibido → lookup en DB. 2. Si no existe: "Este enlace no es válido." 3. Si completed: "Ya completaste tu entrevista. Gracias." 4. Si expired: "Este enlace expiró. Contacta a tu organización." 5. Si valid: SET `token_status=in_progress`, crear Interview si no existe. Retornar `{interview_session, questions[]}`. |
| Bienvenida | Mostrar: nombre de la organización, propósito genérico, garantía de confidencialidad. NO mostrar: nombre del admin, nombres de otros miembros, nombre del miembro (solo "Hola"). |
| Entrevista | Preguntas de a una por pantalla. Progreso visible (X de 15). Tipos: texto libre (textarea), escala 1-5 (radio buttons con labels), opción múltiple (checkboxes). Guardar cada respuesta al avanzar: POST `/interviews/:token/response {question_id, value}`. Si falla: reintento automático 3 veces antes de mostrar error. |
| Persistencia | Si el miembro cierra el browser y vuelve con el mismo link: `Interview.responses` ya tiene sus respuestas parciales. Retomar desde la última pregunta no respondida. |
| Adjuntos opcionales | Solo al final, antes de confirmar envío. Máx 2 archivos, 5 MB. Upload a S3. Guardar referencia en `Interview.attachments` JSONB. |
| Confirmación final | Pantalla: "¿Enviar tus respuestas?" con resumen de preguntas respondidas. Botón "Enviar". POST `/interviews/:token/complete`. Sistema: SET `Interview.status=completed`, SET `Member.token_status=completed`, SET `Interview.completed_at=now()`. Encolar notificación al admin. **IRREVERSIBLE.** |
| Post-envío | Pantalla estática: "Tu aporte fue registrado. Gracias." Sin links adicionales. Sin posibilidad de re-entrar con el mismo token. |

**El miembro NO puede:** ver respuestas de otros, ver los informes, reeditar respuestas enviadas, saber quién más fue entrevistado.

---

## 4. Modelo de datos

Esquema completo para PostgreSQL con SQLModel. Los campos marcados con ★ son nuevos respecto al V1 original.

### 4.1 Entidades

#### Organization

| Campo | Tipo / Restricción | Entra al análisis |
|-------|--------------------|-------------------|
| `id` | UUID PK default `gen_random_uuid()` | — |
| `name` | VARCHAR(120) NOT NULL, INDEX btree | Sí — identificador en reporte |
| `mission` | TEXT NOT NULL | Sí — contexto base |
| `description` | TEXT nullable | Sí |
| `ways_of_working` | TEXT nullable | Sí |
| `sector` | VARCHAR(60) nullable, ENUM: `retail\|salud\|publico\|educacion\|otro` | Sí — calibra benchmarks futuros |
| `created_at` | TIMESTAMPTZ default now() | — |
| `updated_at` | TIMESTAMPTZ auto-update trigger | — |

#### User

| Campo | Tipo / Restricción | Notas |
|-------|--------------------|-------|
| `id` | UUID PK | — |
| `email` | VARCHAR(255) UNIQUE NOT NULL, INDEX único global | Login principal |
| `password_hash` | VARCHAR(255) NOT NULL | bcrypt cost 12 |
| `name` | VARCHAR(120) NOT NULL | — |
| `org_id` | UUID FK → Organization nullable ★ | null = sin organización (onboarding pendiente) |
| `role` | ENUM(admin, viewer) default admin | viewer reservado V2 |
| `failed_login_count` | SMALLINT default 0 ★ | Para bloqueo por intentos |
| `locked_until` | TIMESTAMPTZ nullable ★ | Bloqueo temporal |
| `created_at` | TIMESTAMPTZ default now() | — |

#### Group

| Campo | Tipo / Restricción | Entra al análisis |
|-------|--------------------|-------------------|
| `id` | UUID PK | — |
| `org_id` | UUID FK NOT NULL, INDEX | — |
| `parent_group_id` | UUID FK → Group nullable, INDEX btree | Define jerarquía |
| `name` | VARCHAR(120) NOT NULL, UNIQUE(org_id, name) | Sí |
| `description` | TEXT nullable | Sí |
| `admin_notes` | TEXT nullable | Sí — **NUNCA expuesto a miembros** |
| `depth_level` | SMALLINT NOT NULL default 0, CHECK(depth_level BETWEEN 0 AND 2) | — |
| `deleted_at` | TIMESTAMPTZ nullable ★ | Soft delete |
| `created_at` | TIMESTAMPTZ default now() | — |

#### Member

| Campo | Tipo / Restricción | Entra al análisis |
|-------|--------------------|-------------------|
| `id` | UUID PK | — |
| `org_id` | UUID FK NOT NULL, INDEX | — |
| `group_id` | UUID FK NOT NULL, INDEX | — |
| `name` | VARCHAR(120) NOT NULL | Solo en vistas admin. **NUNCA en reportes** |
| `email` | VARCHAR(255) NOT NULL, UNIQUE(org_id, email) | — |
| `role_description` | TEXT NOT NULL | Sí — calibra peso de respuestas |
| `admin_notes` | TEXT nullable | Sí — **NUNCA visible al miembro** |
| `interview_token_hash` | VARCHAR(64) UNIQUE ★ | SHA-256 del token. **El token real NUNCA se almacena** |
| `token_status` | ENUM(pending, in_progress, completed, expired, abandoned) NOT NULL default pending ★ | Añadido `abandoned` |
| `token_sent_at` | TIMESTAMPTZ nullable | — |
| `token_expires_at` | TIMESTAMPTZ nullable | default: `token_sent_at + interval 14 days` |
| `email_delivery_failed` | BOOLEAN default false ★ | Para indicador en UI admin |
| `deleted_at` | TIMESTAMPTZ nullable ★ | Soft delete |
| `created_at` | TIMESTAMPTZ default now() | — |

#### Interview

| Campo | Tipo / Restricción | Notas |
|-------|--------------------|-------|
| `id` | UUID PK | — |
| `member_id` | UUID FK → Member UNIQUE NOT NULL | Un miembro = una entrevista máximo |
| `org_id` | UUID FK NOT NULL, INDEX | Desnormalizado para queries de análisis |
| `question_schema_version` | VARCHAR(20) NOT NULL default `'v1.0'` ★ | Detecta entrevistas con schema distinto |
| `responses` | JSONB NOT NULL default `'{}'` | Map `{question_id: value}`. Actualización incremental. |
| `attachments` | JSONB nullable | Array `[{file_url, file_name, file_type, file_size_kb, uploaded_at}]` |
| `status` | ENUM(in_progress, completed, abandoned) NOT NULL default in_progress ★ | Añadido `abandoned` |
| `started_at` | TIMESTAMPTZ default now() | — |
| `completed_at` | TIMESTAMPTZ nullable | — |
| `last_activity_at` | TIMESTAMPTZ default now() ★ | Actualizar en cada POST /response |

#### Document

| Campo | Tipo / Restricción | Notas |
|-------|--------------------|-------|
| `id` | UUID PK | — |
| `org_id` | UUID FK NOT NULL, INDEX | — |
| `group_id` | UUID FK nullable, INDEX | Si pertenece a un grupo |
| `uploaded_by` | ENUM(admin, member) NOT NULL ★ | Reemplaza boolean |
| `uploader_member_id` | UUID FK → Member nullable ★ | Quién subió si `uploaded_by=member` |
| `file_url` | TEXT NOT NULL | URL S3 |
| `file_name` | VARCHAR(255) NOT NULL | — |
| `file_type` | VARCHAR(20) NOT NULL | `pdf\|jpg\|png` |
| `file_size_kb` | INTEGER NOT NULL | — |
| `processed_in_job_id` | UUID FK → AnalysisJob nullable ★ | Bloquea delete si está seteado |
| `created_at` | TIMESTAMPTZ default now() | — |

#### StrategicContext

| Campo | Tipo / Restricción | Notas |
|-------|--------------------|-------|
| `id` | UUID PK | — |
| `org_id` | UUID FK **UNIQUE** NOT NULL | Una org = un StrategicContext activo |
| `objectives` | TEXT NOT NULL | Entra al análisis solo en Informe B |
| `concerns` | TEXT NOT NULL | — |
| `key_questions` | TEXT nullable | — |
| `additional_context` | TEXT nullable | — |
| `updated_at` | TIMESTAMPTZ auto-update ★ | Para saber cuándo se modificó |
| `created_at` | TIMESTAMPTZ default now() | — |

#### AnalysisJob

| Campo | Tipo / Restricción | Notas |
|-------|--------------------|-------|
| `id` | UUID PK | — |
| `org_id` | UUID FK NOT NULL, INDEX | — |
| `type` | ENUM(A, B) NOT NULL | A=ciego, B=orientado |
| `strategic_context_id` | UUID FK nullable | Solo para tipo B |
| `input_snapshot` | JSONB NOT NULL | Copia inmutable de todos los datos al momento del análisis |
| `status` | ENUM(queued, processing, completed, failed) NOT NULL default queued | — |
| `result_text` | TEXT nullable | Output del LLM. Formato markdown. |
| `validation_passed` | BOOLEAN nullable ★ | True si pasó validación de nombres propios |
| `retry_of_job_id` | UUID FK → AnalysisJob nullable ★ | Referencia al job original si es reintento |
| `model_used` | VARCHAR(60) nullable | Ej: `gpt-4.1` |
| `tokens_input` | INTEGER nullable | — |
| `tokens_output` | INTEGER nullable | — |
| `error_message` | TEXT nullable | — |
| `queued_at` | TIMESTAMPTZ default now() | — |
| `started_at` | TIMESTAMPTZ nullable | — |
| `completed_at` | TIMESTAMPTZ nullable | — |

#### TokenBlacklist ★ (nueva entidad)

| Campo | Tipo / Restricción | Notas |
|-------|--------------------|-------|
| `token_jti` | VARCHAR(36) PK, INDEX | JTI del JWT (claim `jti`) |
| `invalidated_at` | TIMESTAMPTZ default now() | — |
| `expires_at` | TIMESTAMPTZ NOT NULL | Para purga periódica: `DELETE WHERE expires_at < now()` |

### 4.2 Índices requeridos

**Todos deben estar en el script de migración inicial. No son opcionales.**

| Índice | Justificación |
|--------|---------------|
| `Group(org_id)` | Query principal del dashboard |
| `Group(parent_group_id)` | Construcción del árbol jerárquico |
| `Member(org_id)` | Listado y conteo de miembros por org |
| `Member(group_id)` | Miembros por grupo |
| `Member(interview_token_hash)` | Lookup en cada request de entrevista. UNIQUE. |
| `Interview(org_id)` | Queries de análisis y dashboard |
| `Interview(member_id)` | UNIQUE. Garantía 1:1. |
| `AnalysisJob(org_id, status)` | Índice compuesto: detectar jobs activos por org |
| `AnalysisJob(org_id, completed_at DESC)` | Para GET `/analysis/latest` |
| `Document(org_id)` | Listado de documentos |
| `Document(group_id)` | Documentos por grupo en pipeline |
| `TokenBlacklist(token_jti)` | PK. Lookup en cada request autenticado. |

---

## 5. API — Contratos completos

**Base URL:** `/api/v1`  
**Autenticación:** Bearer JWT en header `Authorization`, excepto endpoints públicos marcados con `[P]`.  
**Soft delete:** todos los GET filtran `WHERE deleted_at IS NULL` por defecto.

### 5.1 Auth

| Método | Ruta | Body | Respuesta | Notas |
|--------|------|------|-----------|-------|
| POST | `/auth/register` | `name, email, password` | `{ user, token }` | Crea User con `org_id=null`. Redirige a onboarding. |
| POST | `/auth/login` | `email, password` | `{ user, token }` | JWT 7 días. Bloquea si `locked_until > now()`. |
| POST | `/auth/logout` | — | 200 OK | Inserta token JTI en `TokenBlacklist`. |
| GET | `/auth/me` | — | `{ user, organization\|null }` | Token válido requerido. |

### 5.2 Organizations

| Método | Ruta | Body / Params | Respuesta |
|--------|------|---------------|-----------|
| POST | `/organizations` | `name, mission, description?, ways_of_working?, sector?` | `{ organization }` |
| GET | `/organizations/:id` | — | `{ organization, completeness_score }` |
| PATCH | `/organizations/:id` | Cualquier campo editable | `{ organization }` |
| GET | `/organizations/:id/dashboard` | — | `{ groups[], completeness, pending_interviews[], latest_job_status }` |

`completeness_score`: objeto con `groups_with_info_pct`, `members_created_count`, `interviews_completed_pct`, `can_generate_A` (boolean), `can_generate_B` (boolean).

### 5.3 Groups

| Método | Ruta | Body / Params | Respuesta |
|--------|------|---------------|-----------|
| POST | `/organizations/:orgId/groups` | `name, description?, parent_group_id?, admin_notes?` | `{ group }` |
| GET | `/organizations/:orgId/groups` | — | `{ groups[] }` — árbol anidado |
| GET | `/organizations/:orgId/groups/:id` | — | `{ group, members[], documents[] }` |
| PATCH | `/organizations/:orgId/groups/:id` | Cualquier campo excepto `parent_group_id` | `{ group }` |
| DELETE | `/organizations/:orgId/groups/:id` | — | 204 — solo si no tiene miembros ni subgrupos activos. 409 si tiene dependencias. |

### 5.4 Members

| Método | Ruta | Body / Params | Respuesta |
|--------|------|---------------|-----------|
| POST | `/organizations/:orgId/members` | `name, email, group_id, role_description, admin_notes?` | `{ member }` + email encolado |
| GET | `/organizations/:orgId/members` | `?group_id=&status=` | `{ members[] }` |
| GET | `/organizations/:orgId/members/:id` | — | `{ member, interview_status }` — **SIN** `Interview.responses` |
| PATCH | `/organizations/:orgId/members/:id` | Cualquier campo excepto `email` e `interview_token_hash` | `{ member }` |
| DELETE | `/organizations/:orgId/members/:id` | — | 204 — soft delete |
| POST | `/organizations/:orgId/members/:id/resend-invite` | — | 200 o 409 si ya completado |

### 5.5 Interviews — Flujo del miembro `[P]`

Todos los endpoints de esta sección son **públicos**. Autenticación por token en URL.

| Método | Ruta | Body | Respuesta |
|--------|------|------|-----------|
| GET | `/interviews/:token` | — | `{ interview_session, questions[] }` |
| POST | `/interviews/:token/response` | `question_id, value` | `{ saved: true, progress: {answered, total} }` |
| POST | `/interviews/:token/complete` | — | `{ completed: true }` — **IRREVERSIBLE** |
| POST | `/interviews/:token/attach` | `file (multipart)` | `{ attachment_url }` |

`GET /interviews/:token` NO retorna: `member.name`, `member.email`, `admin_notes` (de member ni de group), ni información sobre otros miembros.

### 5.6 Documents

| Método | Ruta | Notas |
|--------|------|-------|
| POST | `/organizations/:orgId/documents` | Multipart. `group_id` o `uploader_member_id` en body. |
| GET | `/organizations/:orgId/documents` | `?group_id=` para filtrar |
| DELETE | `/organizations/:orgId/documents/:id` | 409 si `processed_in_job_id IS NOT NULL` |

### 5.7 Diagnóstico

| Método | Ruta | Body | Respuesta |
|--------|------|------|-----------|
| POST | `/organizations/:orgId/strategic-context` | `objectives, concerns, key_questions?, additional_context?` | `{ context }` — **UPSERT, no INSERT** |
| GET | `/organizations/:orgId/strategic-context` | — | `{ context \| null }` |
| POST | `/organizations/:orgId/analysis/trigger` | — | `{ job_a_id, job_b_id?, status: 'queued' }` o 422 con condiciones faltantes o 409 si hay job activo |
| GET | `/organizations/:orgId/analysis/jobs` | — | `{ jobs[] }` — historial completo |
| GET | `/organizations/:orgId/analysis/jobs/:jobId` | — | `{ job con result_text }` |
| GET | `/organizations/:orgId/analysis/latest` | — | `{ job_a, job_b? }` — el par más reciente completado |
| POST | `/organizations/:orgId/analysis/jobs/:jobId/retry` | — | `{ new_job_id }` — crea nuevo job con `retry_of_job_id` |

---

## 6. Reglas de negocio

Todas son técnicamente ejecutadas. Ninguna depende de la buena voluntad del usuario.

### 6.1 Condiciones para generar diagnóstico (R1–R5)

R1: Organization.name NOT NULL AND Organization.mission NOT NULL AND len(mission) >= 20
R2: COUNT(Group WHERE org_id=X AND deleted_at IS NULL AND description IS NOT NULL) >= 1
R3: COUNT(Member WHERE org_id=X AND deleted_at IS NULL) >= 3
R4: COUNT(Member WHERE org_id=X AND deleted_at IS NULL AND group_id IN (grupos que pasan R2)) >= 3
R5: (COUNT(Interview WHERE org_id=X AND status=completed) / COUNT(Member WHERE org_id=X AND deleted_at IS NULL AND token_status != 'expired')) >= 0.60
- **Informe A:** se genera si R1–R5 se cumplen. `StrategicContext` NO requerido.
- **Informe B:** se genera ADICIONALMENTE si existe `StrategicContext` con `objectives` y `concerns` NOT NULL.
- Si hay job `queued|processing` para esta org: retornar 409 con `job_id` del job activo.

### 6.2 Confidencialidad — reglas técnicas

| Regla | Implementación técnica |
|-------|------------------------|
| Respuestas individuales no atribuibles | Pipeline agrega respuestas por grupo antes de construir el prompt. Nunca se incluye `member.name` en ningún bloque del prompt. |
| `admin_notes` de miembro: invisible al miembro | GET `/interviews/:token` NO retorna ningún campo de Member excepto `group_id`. Serializar Interview sin join a Member. |
| Un miembro no ve el estado de otros | GET `/interviews/:token` retorna solo la Interview del token usado. No retorna lista de miembros ni estadísticas de completitud. |
| Reportes sin nombres propios | Fase F7 del pipeline: regex de nombres propios + LLM-as-judge si regex encuentra matches. Si falla validación: reintento con instrucción reforzada. Máx 2 reintentos; si persiste: `status=failed`. |
| Admin no puede ver responses individuales | No existe endpoint GET que retorne `Interview.responses` completos para el admin. GET `/members/:id` retorna solo `token_status`. |

### 6.3 Tokens de entrevista

| Situación | Comportamiento del sistema |
|-----------|---------------------------|
| Token válido (pending/in_progress, no expirado) | Acceso concedido. Si `status=pending`: cambiar a `in_progress`. Crear Interview si no existe. |
| Token expirado | HTTP 410. "Este enlace expiró." No crear Interview. |
| Token completado | HTTP 200. "Ya completaste tu entrevista. Gracias." |
| Token no encontrado | HTTP 404. Mensaje genérico: "Este enlace no es válido." |
| Token abandoned | Tratarlo como token válido si no ha expirado. Si expirado: mensaje de expirado. |
| Reenvío de invitación | Generar nuevo token (UUID v4). Hashear y guardar nuevo hash (reemplaza hash anterior). Actualizar `token_sent_at` y `token_expires_at`. Si status era `expired`: cambiar a `pending`. Si `in_progress`: no cambiar. Encolar email con nuevo token. |
| Concurrencia (mismo token, dos browsers) | La entrevista es idempotente por `question_id`. POST `/response` con mismo `question_id` sobrescribe. Sin conflicto real. |

### 6.4 Límites y validaciones V1

| Recurso | Límite | Acción si se supera |
|---------|--------|---------------------|
| Grupos por org | MAX 20 (incl. soft-deleted) | HTTP 422 con mensaje explícito |
| Profundidad de subgrupos | MAX 3 niveles (depth 0, 1, 2) | HTTP 422. CHECK constraint en DB. |
| Miembros por org | MAX 50 activos (`deleted_at IS NULL`) | HTTP 422 |
| Docs por grupo | MAX 5 archivos | HTTP 422 antes de subir |
| Tamaño total docs por grupo | MAX 10 MB | HTTP 422. Validar antes de subir a S3. |
| Archivos por miembro | MAX 2 en `Interview.attachments` | HTTP 422 |
| Tamaño archivo miembro | MAX 5 MB por archivo | HTTP 422 |
| Análisis simultáneos | MAX 1 activo (queued/processing) por org | HTTP 409 con `job_id` del activo |
| Intentos de login fallidos | MAX 5 en ventana de 5 min | Bloquear User 5 min (`locked_until`) |
| Timeout de análisis | MAX 15 min por job | Worker cancela job. `status=failed`. `error_message="Timeout"`. |

---

## 7. Estados del sistema

Las transiciones no listadas aquí son inválidas y deben retornar 422.

### 7.1 Member.token_status

| Transición | Condición / Trigger |
|------------|---------------------|
| → `pending` | Estado inicial al crear Member. También desde `expired` vía resend-invite. |
| `pending` → `in_progress` | Miembro abre el link (GET `/interviews/:token`, token válido). |
| `in_progress` → `completed` | POST `/interviews/:token/complete` ejecutado con éxito. |
| `in_progress` → `abandoned` | Admin hace soft-delete del Member mientras entrevista está `in_progress`. |
| `pending \| in_progress` → `expired` | Cron cada hora: UPDATE Member SET `token_status=expired` WHERE `token_expires_at < now()` AND `token_status IN ('pending', 'in_progress')`. |
| `expired` → `pending` | Admin ejecuta resend-invite. |
| `completed` → (nada) | Estado terminal. |
| `abandoned` → (nada) | Estado terminal. |

### 7.2 Interview.status

| Transición | Condición / Trigger |
|------------|---------------------|
| → `in_progress` | Se crea automáticamente cuando el miembro accede al token por primera vez. |
| `in_progress` → `completed` | POST `/interviews/:token/complete`. Irreversible. |
| `in_progress` → `abandoned` | Admin hace soft-delete del Member. |
| `completed` → (nada) | Estado terminal. |
| `abandoned` → (nada) | Estado terminal. |

### 7.3 AnalysisJob.status

| Transición | Condición / Trigger |
|------------|---------------------|
| → `queued` | POST `/analysis/trigger` crea el job. |
| `queued` → `processing` | Worker toma el job de la cola. |
| `processing` → `completed` | Pipeline ejecutado con éxito y validación pasada. |
| `processing` → `failed` | Error en cualquier fase del pipeline, o timeout (>15 min), o validación de nombres falla después de 2 reintentos. |
| `failed` → `queued` | Admin ejecuta "Reintentar" desde UI. Se crea nuevo job con `retry_of_job_id = job_id` fallido. |
| `completed` → (nada) | Estado terminal. |

### 7.4 Completeness score (calculado, no persistido)

groups_with_info_pct = COUNT(Group WHERE org_id=X AND description IS NOT NULL AND deleted_at IS NULL) / COUNT(Group WHERE org_id=X AND deleted_at IS NULL) * 100
members_created_count = COUNT(Member WHERE org_id=X AND deleted_at IS NULL)
interviews_completed_pct = COUNT(Interview WHERE org_id=X AND status='completed') / NULLIF(COUNT(Member WHERE org_id=X AND deleted_at IS NULL AND token_status != 'expired'), 0) * 100
can_generate_A = evaluación de R1–R5 can_generate_B = can_generate_A AND StrategicContext NOT NULL
---

## 8. Eventos y procesos sync + async

### 8.1 Procesos síncronos (en el request)

| Proceso | Descripción |
|---------|-------------|
| Validación de token de entrevista | En cada GET `/interviews/:token`: hash SHA-256 del token recibido → lookup en DB → validar estado y expiración. < 50ms esperado. |
| Guardado incremental de respuesta | POST `/interviews/:token/response`: UPDATE Interview SET `responses = responses \|\| {question_id: value}`. Operación JSONB merge en PostgreSQL. Atómica. |
| Cálculo de completeness_score | GET `/dashboard`: ejecutar 3 queries COUNT en el momento. No cachear en V1. < 100ms esperado. |
| Validación de condiciones para análisis | POST `/analysis/trigger`: ejecutar R1–R5 en el request antes de crear jobs. Si falla: 422 con detalle de qué condición falta. |

### 8.2 Procesos asíncronos (worker / queue)

| Proceso | Descripción y especificación |
|---------|------------------------------|
| Envío de email de invitación | Trigger: POST `/members`. Encolar tarea `{member_id, token (texto plano, solo en este momento)}`. Worker: construir email con link `https://app.domain/entrevista/{token}`. Si falla: retry 3 veces con backoff. Si falla definitivamente: SET `member.email_delivery_failed=true`. Admin ve indicador en UI. |
| Notificación al admin (entrevista completada) | Trigger: POST `/interviews/:token/complete`. Email al admin: "Un miembro completó su entrevista. Progreso actual: X de Y." Sin nombre del miembro en el email. |
| Expiración de tokens | Cron cada hora. UPDATE Member SET `token_status='expired'` WHERE `token_expires_at < now()` AND `token_status IN ('pending', 'in_progress')`. Log de cuántos se expiraron. |
| Pipeline de análisis | Ver sección 9. |
| Purga de TokenBlacklist | Cron cada 24h. DELETE FROM TokenBlacklist WHERE `expires_at < now()`. |

---

## 9. Pipeline de análisis

Ejecutado por worker al tomar job de la cola. Cada fase es atómica. Si falla cualquier fase: SET `job.status=failed` con error en `error_message`. **A partir de F1, el pipeline usa SOLO el snapshot (nunca leer de DB directamente).**

| Fase | Descripción ejecutable | Output |
|------|------------------------|--------|
| **F1: Snapshot** | Leer todos los datos de la org: `{organization, groups[], members[] (sin interview_token_hash, sin name, sin email), interviews[] (responses completos), documents[], strategic_context\|null}`. Guardar en `AnalysisJob.input_snapshot`. | JSONB inmutable en DB |
| **F2: Contexto estructural** | Construir texto: "ORGANIZACIÓN: {name}. MISIÓN: {mission}. DESCRIPCIÓN: {description}. MODO DE TRABAJO: {ways_of_working}. ESTRUCTURA: [para cada grupo: nombre, descripción, admin_notes, subgrupos anidados, roles de sus miembros (sin nombres), admin_notes de miembros]." | String: `bloque_estructura` |
| **F3: Pre-aggregation** | Para CADA grupo con miembros entrevistados: llamar a LLM (`gpt-4o-mini`, temp=0.1) con prompt: "Agrega las respuestas de múltiples personas del grupo {nombre_grupo} a la pregunta {pregunta}. NO menciones nombres. Sintetiza en 3-5 oraciones las perspectivas comunes y divergentes: {respuestas[]}." Resultado: `{group_id: {question_id: texto_agregado}}`. Si el grupo tiene 0 entrevistas completadas: omitir del bloque. | JSON: `aggregated_responses` |
| **F4: Procesamiento de documentos** | Para cada Document de la org: si `file_type=pdf` → extraer texto (pdftotext o Textract). Truncar a 2000 tokens por documento. Construir bloque: "DOCUMENTOS DE CONTEXTO: [{file_name}: {texto_truncado}]". Si suma de docs > 8000 tokens: resumir el bloque con LLM antes de incluir. | String: `bloque_documentos` |
| **F5: Construcción del prompt** | User message: `bloque_estructura` + `"\n\n"` + `bloque_perspectivas` (de F3) + `"\n\n"` + `bloque_documentos` (de F4) + (solo tipo B) + `"\n\nCONTEXTO ESTRATÉGICO: "` + `{objectives, concerns, key_questions}`. Estimar tokens. Si > 90k: truncar `bloque_perspectivas` empezando por grupos más pequeños. | String: `prompt_final` |
| **F6: LLM call** | POST a API OpenAI (`gpt-4.1`, `temperature=0.3`, `max_tokens=4000`). Guardar `model_used`, `tokens_input`, `tokens_output`. Timeout: 120s. Si error de API (5xx) o timeout: raise para que el job quede `failed`. | String: `raw_output` |
| **F7: Validación de nombres** | Verificar que `raw_output` NO contiene ningún `member.name` del snapshot (comparación case-insensitive). Si encuentra: reintentar F6 con instrucción adicional: "CRÍTICO: El análisis no debe mencionar ningún nombre propio de persona." Máx 2 reintentos. Si persiste: `status=failed`. | String: `validated_output` |
| **F8: Verificación estructural ★** | Verificar que `validated_output` contiene las secciones requeridas (regex de headers). Si faltan secciones: log de advertencia (no falla el job en V1, registrar en `error_message` como warning). | Boolean: `structure_ok` |
| **F9: Guardado** | UPDATE AnalysisJob SET `result_text=validated_output`, `status='completed'`, `completed_at=now()`, `validation_passed=true`. SET `processed_in_job_id` en Documents usados. Encolar notificación al admin: "Tu diagnóstico está listo." | Job completado |

### System prompt (ambos informes)

Eres un analista institucional experto en organizaciones. Tu tarea es producir un diagnóstico riguroso.
Reglas absolutas:
	1	Nunca mencionar nombres propios de personas.
	2	Atribuir siempre a grupos, no a individuos.
	3	Distinguir explícitamente entre lo que la organización declara formalmente y lo que las perspectivas internas revelan.
	4	No incluir recomendaciones en este informe — solo diagnóstico.
	5	Responde siempre en español, independientemente del idioma de las respuestas de los entrevistados.
### Bloque adicional para Informe B (al final del user message)

CONTEXTO ESTRATÉGICO DEL CLIENTE: Objetivos: {objectives} Preocupaciones: {concerns} Preguntas clave: {key_questions}
Orienta el análisis hacia estas prioridades sin ignorar hallazgos que las contradigan.
---

## 10. Output del sistema — Reportes

### 10.1 Estructura del output esperado

El LLM debe producir el output con estas secciones exactas (usadas en F8 para verificación estructural):

**Informe A (7 secciones):**

1. **Síntesis ejecutiva** — 3-5 oraciones. La tensión central de la organización.
2. **Estructura real vs. formal** — Comparación entre lo declarado y lo que revelan las perspectivas internas.
3. **Dinámica de actores y poder** — Quién concentra poder, cómo se ejerce, dependencias críticas.
4. **Procesos críticos** — Los 2-3 procesos que más determinan el desempeño. Brechas en cada uno.
5. **Incentivos y desalineaciones** — Qué comportamientos incentiva el sistema actualmente.
6. **Diagnóstico de valor integral** — Balance eficiencia vs. bienestar. Clasificación: óptimo / eficiencia sin personas / bienestar sin resultados / disfunción.
7. **Hipótesis diagnósticas** — 3-5 hipótesis concretas sobre por qué la organización funciona como funciona.

**Informe B (8 secciones = 7 anteriores + 1):**

8. **Lectura estratégica** — Cómo los hallazgos se relacionan con los objetivos declarados. Qué está alineado, qué está en tensión.

### 10.2 Clasificación de valor integral

| Escenario | Eficiencia | Bienestar | Diagnóstico |
|-----------|-----------|-----------|-------------|
| Óptimo institucional | Alta | Alto | Modelo de referencia |
| Eficiencia sin personas | Alta | Bajo | Riesgo de agotamiento y rotación |
| Bienestar sin resultados | Baja | Alto | Insostenible en el tiempo |
| Disfunción institucional | Baja | Bajo | Crisis organizacional |

---

## 11. Banco de preguntas

Schema fijo en V1. Vive en el código, no en la DB. Referenciado en `question_schema_version='v1.0'`.

| ID | Lente | Pregunta | Tipo |
|----|-------|----------|------|
| `q_str_1` | Estructura | Describe cómo está organizado tu equipo o área. ¿Quiénes son las personas clave y qué rol cumple cada una? | Texto libre |
| `q_str_2` | Estructura | ¿Ha cambiado la forma en que está organizado tu equipo en el último año? ¿Qué lo provocó? | Texto libre |
| `q_prc_1` | Procesos | Describe el proceso más importante de tu trabajo diario, paso a paso, desde que empieza hasta que termina. | Texto libre |
| `q_prc_2` | Procesos | ¿Cuánto de ese proceso funciona como debería en la práctica? ¿Dónde se traba o se complica con más frecuencia? | Escala 1-5 + texto |
| `q_prc_3` | Procesos | ¿Qué información o recurso te falta con más frecuencia para hacer bien tu trabajo? | Texto libre |
| `q_rules_1` | Reglas | ¿Hay normas o procedimientos formales que en la práctica se omiten o se hacen diferente? Describe un ejemplo reciente. | Texto libre |
| `q_rules_2` | Reglas | ¿Cuánto de lo que ocurre en tu área está escrito o formalizado versus depende de acuerdos informales y costumbre? | Escala 1-5 + texto |
| `q_inc_1` | Incentivos | ¿Qué comportamientos son los más reconocidos o recompensados en tu organización, aunque no estén escritos en ningún lado? | Texto libre |
| `q_inc_2` | Incentivos | ¿Hay situaciones donde hacer lo correcto para la organización te cuesta algo a ti personalmente (tiempo, reconocimiento, comodidad)? | Texto libre |
| `q_pow_1` | Poder | ¿Quién toma las decisiones que más afectan tu trabajo? ¿Puedes influir en esas decisiones? ¿Cómo? | Texto libre |
| `q_pow_2` | Poder | Si mañana quisieras cambiar algo de cómo funciona tu área, ¿qué tan fácil o difícil sería lograrlo? ¿Por qué? | Escala 1-5 + texto |
| `q_ep_1` | Episodios | Describe una situación reciente en la que algo salió claramente mal. ¿Qué pasó, por qué, y cómo se resolvió? | Texto libre |
| `q_ep_2` | Episodios | Describe una situación reciente en la que algo funcionó especialmente bien. ¿Qué lo hizo posible? | Texto libre |
| `q_wb_1` | Bienestar | ¿Cómo describirías el nivel de energía o motivación de tu equipo en este momento? (1=agotado, 5=motivado y enfocado) | Escala 1-5 + texto |
| `q_wb_2` | Bienestar | ¿Hay aspectos de cómo trabajan que sientes que desgastan al equipo innecesariamente? | Texto libre |

Las respuestas de escala se cuantifican. Las de texto libre se agregan por grupo (F3) antes de entrar al análisis. **Nunca se incluyen textualmente en el prompt.**

---

## 12. Decisiones de producto

Cada decisión cierra una ambigüedad. Son firmes para V1.

| ID | Decisión | Justificación |
|----|----------|---------------|
| D1 | El email de invitación al miembro dice: "[Nombre Org] te invita a compartir tu perspectiva en un diagnóstico organizacional. Tu aporte es confidencial y se analiza de forma agregada. Tus respuestas individuales no serán atribuidas a ti. → [Comenzar entrevista]" | Transmite confidencialidad sin prometer anonimato absoluto. "Perspectiva" es más neutro que "evaluación". |
| D2 | El miembro NO sabe qué porcentaje del equipo ha respondido. El admin SÍ lo ve en el dashboard. | Mostrar el % al miembro podría presionarlo o desmotivarlo. El admin necesita el dato para gestionar. |
| D3 | Re-diagnóstico permitido sin restricciones. Cada trigger crea nuevos jobs. Sin límite de análisis por organización en V1. | Simplicidad. El costo es por tokens, no por análisis. Restricciones de costo son problema de pricing, no de producto. |
| D4 | El LLM siempre responde en español. Forzado en el system prompt. | Simplicidad V1. Evita outputs mezclados. El admin colombiano espera español. |
| D5 | Notificaciones al admin: (1) cuando cada miembro completa su entrevista, (2) cuando el diagnóstico está listo. Sin notificación al 60%. | Dos eventos claros. La notificación al 60% es compleja (¿qué pasa si un miembro se elimina y el % baja?). Diferido a V2. |
| D6 | Retención de datos: 90 días después de que el admin cierre la cuenta. Aviso por email 30 días antes. Exportación = endpoint protegido que genera ZIP (JSON dump de Organization + AnalysisJobs). Sin UI de exportación en V1. | Suficiente para cumplir expectativa de usuario. |
| Dold1 | El schema de preguntas vive en el código, no en la DB. Set fijo en V1. | `question_schema_version` en Interview es suficiente para detectar cambios futuros. |
| Dold2 | Informe A puede generarse sin `StrategicContext`. | Un diagnóstico parcial con datos reales vale más que esperar completitud. Principio P4. |
| Dold3 | Profundidad máxima de grupos: 3 niveles (depth 0, 1, 2). | La mayoría de orgs tiene menos de 3 niveles reales. Simplifica árbol de UI y pipeline. |
| Dold4 | El token de entrevista se almacena como hash (SHA-256), no en texto plano. | El token es un credential. Almacenarlo en texto plano es una vulnerabilidad. |

---

## 13. Riesgos de construcción agéntica

### 13.1 Riesgos críticos — el agente lo hará mal sin instrucción explícita

| Riesgo | Por qué el agente lo comete | Mitigación |
|--------|----------------------------|------------|
| Almacenar el token de entrevista en texto plano | El patrón más común en tutoriales. El agente no sabe que es un credential. | Especificar en cada prompt de construcción: "`interview_token_hash` almacena SHA-256 del token. El token real nunca se almacena." |
| Incluir `member.name` o `admin_notes` en el prompt del LLM | El agente construirá el contexto incluyendo todos los campos de Member por defecto. | El prompt de construcción del pipeline debe listar EXPLÍCITAMENTE qué campos se excluyen del snapshot: `[name, email, interview_token_hash]`. |
| Implementar DELETE hard en lugar de soft delete | DELETE es el comportamiento default de cualquier ORM. | Especificar en el schema: "Member y Group usan soft delete. Nunca DELETE real. Siempre `SET deleted_at=now()`." |
| Ignorar el índice compuesto en `AnalysisJob(org_id, status)` | Los agentes rara vez añaden índices compuestos espontáneamente. | Incluir el script de creación de índices en el mismo archivo de migraciones. |
| Hacer la llamada al LLM síncrona en el request del trigger | La implementación más simple es síncrona. El agente no anticipará timeouts. | Especificar: "POST `/analysis/trigger` solo encola el job y retorna inmediatamente. El pipeline corre en worker separado." |
| Concatenar respuestas crudas de miembros directamente en el prompt principal | Es la implementación más obvia. El agente no sabe que esto puede exponer individuos o sobrepasar la ventana de contexto. | Especificar la fase F3 (pre-aggregation) como un paso obligatorio antes del prompt principal. |

### 13.2 Riesgos moderados

| Riesgo | Probabilidad | Mitigación |
|--------|-------------|------------|
| Endpoint GET `/members/:id` expone `Interview.responses` al admin | Alta — el agente seguirá el patrón CRUD estándar | Especificar: "GET `/members/:id` retorna solo campos de Member + `token_status`. No hay endpoint admin que retorne `Interview.responses`." |
| Calcular el 60% incluyendo miembros con token expirado en el denominador | Media | Incluir la fórmula exacta de R5 en la especificación del endpoint `/analysis/trigger`. |
| No implementar el retry de la llamada al LLM en F7 | Media | Especificar: "Si validación de nombres falla: reintento de F6 con instrucción adicional. Máx 2 reintentos." |
| Crear múltiples `StrategicContext` en lugar de uno por org (UPSERT) | Media | Especificar: "UNIQUE(`org_id`) en `StrategicContext`. POST `/strategic-context` hace UPSERT, no INSERT." |
| No invalidar el token anterior al reenviar invitación | Alta | Especificar: "Al regenerar token: el nuevo hash reemplaza al anterior en Member. El hash anterior deja de ser válido." |

---

## 14. Checklist de verificación

Antes de marcar cualquier módulo como completo, verificar:

- [ ] `interview_token_hash` almacena SHA-256. El token real nunca toca la DB.
- [ ] GET `/interviews/:token` no retorna `admin_notes` ni `name` del miembro.
- [ ] El pipeline de análisis usa pre-aggregation (F3) antes del prompt principal.
- [ ] El prompt del LLM no incluye ningún `member.name`.
- [ ] Member y Group tienen `deleted_at`. Todos los queries filtran `WHERE deleted_at IS NULL`.
- [ ] POST `/analysis/trigger` es asíncrono: encola job y retorna inmediatamente.
- [ ] `StrategicContext` tiene `UNIQUE(org_id)`. El endpoint hace UPSERT.
- [ ] Los índices de DB están en el script de migración inicial.
- [ ] El cron de expiración de tokens corre cada hora.
- [ ] GET `/members/:id` del admin NO retorna `Interview.responses`.
- [ ] `AnalysisJob.input_snapshot` NO incluye `member.name`, `member.email`, ni `interview_token_hash`.
- [ ] POST `/strategic-context` hace UPSERT (no INSERT) sobre `UNIQUE(org_id)`.
- [ ] El botón "Generar diagnóstico" evalúa R1–R5 en tiempo real y muestra tooltip con condiciones faltantes.
- [ ] El Informe B solo se genera si existe `StrategicContext` con `objectives` y `concerns` NOT NULL.
- [ ] El email de notificación al admin cuando completa un miembro NO incluye el nombre del miembro.
- [ ] `alembic upgrade head` se ejecuta en el entrypoint del contenedor antes de que FastAPI acepte requests.

---

> **Este documento es la única fuente de verdad.**  
> Versión FINAL — Abril 2026 — Para construcción agéntica V1