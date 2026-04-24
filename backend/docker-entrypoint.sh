#!/bin/sh
set -e

# Apply DB migrations on every container start (idempotent)
echo "[entrypoint] Running alembic upgrade head..."
alembic upgrade head

echo "[entrypoint] Starting: $@"
exec "$@"
