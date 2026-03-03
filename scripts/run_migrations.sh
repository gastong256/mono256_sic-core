#!/usr/bin/env bash
set -euo pipefail

echo "Applying database migrations..."
python manage.py migrate --noinput

if [[ "${LOAD_BASE_CHART_ON_MIGRATE:-false}" == "true" ]]; then
  echo "Loading base chart of accounts..."
  python manage.py load_chart_of_accounts
fi

echo "Migrations completed."
