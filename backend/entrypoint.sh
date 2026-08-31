#!/bin/sh
set -e

echo "Waiting for postgres..."
until pg_isready -h "${POSTGRES_HOST:-postgres}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-supplychainx}"; do
  sleep 1
done

echo "Running migrations..."
alembic upgrade head

if [ "$SEED_ON_START" = "true" ]; then
  echo "Seeding database..."
  python -m app.utils.seed
fi

reload_flag=""
if [ "${ENVIRONMENT:-development}" = "development" ]; then
  reload_flag="--reload"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 $reload_flag
