#!/usr/bin/env bash
set -euo pipefail

echo "Checking test database connectivity..."

PYTHON_BIN=".venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python"
fi

DJANGO_SETTINGS_MODULE=config.settings.test "$PYTHON_BIN" - <<'PY'
import os
import sys

import django
from django.db import connections
from django.db.utils import OperationalError

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
django.setup()

try:
    connections["default"].ensure_connection()
except OperationalError as exc:
    print("ERROR: test database is not reachable.")
    print("Hint: start postgres with `docker compose up -d postgres`.")
    print("Hint: verify DATABASE_URL points to a running PostgreSQL instance.")
    print(f"Details: {exc}")
    sys.exit(1)

print("Test database connectivity OK.")
PY
