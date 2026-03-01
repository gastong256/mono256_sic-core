#!/usr/bin/env bash
# Usage: ./scripts/readiness_check.sh [host] [max_attempts]
#   Polls /readyz until it returns 200 or gives up.
set -euo pipefail

HOST="${1:-http://localhost:${PORT:-8000}}"
MAX="${2:-30}"
SLEEP=2

echo "Waiting for $HOST/readyz..."

for i in $(seq 1 "$MAX"); do
    status=$(curl -s -o /dev/null -w "%{http_code}" "$HOST/readyz" || true)
    if [[ "$status" == "200" ]]; then
        echo "Service is ready (attempt $i)."
        exit 0
    fi
    echo "  attempt $i/$MAX — status $status, retrying in ${SLEEP}s..."
    sleep "$SLEEP"
done

echo "ERROR: Service did not become ready after $MAX attempts."
exit 1
