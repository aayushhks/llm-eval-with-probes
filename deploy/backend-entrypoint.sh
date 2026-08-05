#!/bin/sh
# Apply migrations, then serve. Runs from /srv/backend, where alembic.ini lives.
set -e

echo "[entrypoint] applying database migrations"
alembic upgrade head

echo "[entrypoint] starting api on :8000 (${UVICORN_WORKERS:-1} worker(s))"
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${UVICORN_WORKERS:-1}"
