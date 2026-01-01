#!/bin/sh
set -e

echo "🔧 Fixing alembic version if needed..."
python scripts/fix_alembic_version.py

echo "🗄️  Running database migrations..."
alembic upgrade head

echo "🚀 Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"
