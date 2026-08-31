#!/usr/bin/env bash
set -euo pipefail

echo "Running database migrations..."
alembic upgrade head

if [ "${SEED_ON_START:-false}" = "true" ]; then
  echo "Seeding database (SEED_ON_START=true)..."
  python -m app.utils.seed
fi

PORT="${PORT:-8000}"
echo "Starting API on port ${PORT}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
