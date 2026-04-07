# Sprint 1 readiness audit (FastAPI + Next.js)

Fecha: 2026-04-07

## Resultado rápido
- Base **casi lista** para Sprint 1.
- Estructura backend/frontend existe y auth básica está conectada.
- Hay bloqueadores de ejecución en este entorno (no hay Docker CLI), por lo que la validación de runtime quedó en revisión estática.

## Checklist evaluado
1. Docker (backend/frontend/postgres): definido en `docker-compose.yml`.
2. Migraciones al inicio: `backend/entrypoint.sh` ejecuta `alembic upgrade head`.
3. Seed inicial: `backend/seed.py` crea organización default, grupo default y superadmin.
4. `/auth/login`: endpoint existe en `backend/app/routers/auth.py`.
5. Frontend login y `/admin`: existen `/login` y `/admin` (`frontend/app/login/page.tsx`, `frontend/app/(admin)/admin/page.tsx`).

## Riesgos / posibles bloqueadores Sprint 1
- No se pudo confirmar levantamiento real con Docker en este entorno (`docker: command not found`).
- En frontend, `JWTPayload` espera `user_id`, pero el backend emite `sub`; puede romper UI que lea `session.user_id`.
- El backend no agrega `role` ni `organization_id` al JWT de acceso; middleware/frontend no tiene claims completos para autorización por rol en cliente.
- El login frontend no envía `credentials: "include"`; el cookie `refresh_token` del backend puede no persistir en flujo cross-origin (localhost:3000 -> localhost:8000).
