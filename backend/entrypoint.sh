#!/usr/bin/env bash
set -euo pipefail

export PATH="/app/.venv/bin:${PATH}"

DB_HOST="${POSTGRES_HOST:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_NAME="${POSTGRES_DB:-laboratorio}"

log() {
  echo "[entrypoint] $1"
}

log "Esperando a Postgres en ${DB_HOST}:${DB_PORT} (db=${DB_NAME}, user=${DB_USER})..."
until pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1; do
  log "Postgres aún no está disponible; reintentando en 2s..."
  sleep 2
done
log "Postgres disponible."

log "Ejecutando migraciones: alembic upgrade head"
alembic upgrade head
log "Migraciones completadas."

log "Ejecutando seed inicial: python seed.py"
python seed.py
log "Seed completado."

log "Iniciando FastAPI con uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
