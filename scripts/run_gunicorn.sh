#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8000}"
WEB_CONCURRENCY="${WEB_CONCURRENCY:-2}"
GUNICORN_WORKER_CLASS="${GUNICORN_WORKER_CLASS:-sync}"
GUNICORN_THREADS="${GUNICORN_THREADS:-1}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-30}"
GUNICORN_GRACEFUL_TIMEOUT="${GUNICORN_GRACEFUL_TIMEOUT:-30}"
GUNICORN_KEEPALIVE="${GUNICORN_KEEPALIVE:-2}"
GUNICORN_ACCESS_LOG="${GUNICORN_ACCESS_LOG:-false}"

GUNICORN_ARGS=(
  --bind "0.0.0.0:${PORT}"
  --workers "${WEB_CONCURRENCY}"
  --worker-class "${GUNICORN_WORKER_CLASS}"
  --threads "${GUNICORN_THREADS}"
  --timeout "${GUNICORN_TIMEOUT}"
  --graceful-timeout "${GUNICORN_GRACEFUL_TIMEOUT}"
  --keep-alive "${GUNICORN_KEEPALIVE}"
  --error-logfile -
)

if [[ "${GUNICORN_ACCESS_LOG}" == "true" ]]; then
  GUNICORN_ARGS+=(--access-logfile -)
fi

exec gunicorn "${GUNICORN_ARGS[@]}" config.wsgi:application
