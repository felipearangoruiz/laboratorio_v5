#!/usr/bin/env bash
set -euo pipefail

if [[ "$(pwd)" != "/app" ]]; then
  echo "Error: ./scripts/init_db.sh debe ejecutarse desde /app dentro del contenedor backend." >&2
  exit 1
fi

echo "[init_db] Running migrations..."
uv run alembic upgrade head

echo "[init_db] Running seed..."
uv run python seed.py

echo "[init_db] Done."
