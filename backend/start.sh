#!/bin/sh
set -e
cd /app/backend
export PYTHONPATH=/app/backend
PORT="${PORT:-7860}"
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
