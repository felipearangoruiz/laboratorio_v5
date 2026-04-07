#!/bin/bash
set -Eeuo pipefail

PYTHON_BIN="/app/.venv/bin/python"

DB_HOST="${POSTGRES_HOST:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_NAME="${POSTGRES_DB:-laboratorio}"

log() {
  echo "[entrypoint] $*"
}

run_step() {
  local label="$1"
  shift

  log "START: ${label}"
  if "$@"; then
    log "OK: ${label}"
  else
    local code=$?
    log "ERROR: ${label} (exit=${code})"
    exit "${code}"
  fi
}

log "Esperando Postgres en ${DB_HOST}:${DB_PORT} (db=${DB_NAME}, user=${DB_USER})"
until pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1; do
  log "Postgres no disponible todavía; reintentando en 2s..."
  sleep 2
done
log "Postgres disponible"

run_step "Migraciones (alembic upgrade head)" \
  "${PYTHON_BIN}" -m alembic upgrade head

run_step "Seed inicial (python seed.py)" \
  "${PYTHON_BIN}" seed.py

log "START: Uvicorn"
exec "${PYTHON_BIN}" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
