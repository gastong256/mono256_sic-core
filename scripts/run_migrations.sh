#!/usr/bin/env bash
set -euo pipefail

MIGRATE_VERBOSITY="${MIGRATE_VERBOSITY:-1}"

echo "Applying database migrations..."
python manage.py migrate --noinput --verbosity "${MIGRATE_VERBOSITY}"

if [[ "${LOAD_BASE_CHART_ON_MIGRATE:-false}" == "true" ]]; then
  echo "Loading base chart of accounts..."
  python manage.py load_chart_of_accounts
fi

if [[ "${COLLECTSTATIC_ON_MIGRATE:-true}" == "true" ]]; then
  echo "Collecting static files..."
  python manage.py collectstatic --noinput
fi

echo "Migrations completed."
