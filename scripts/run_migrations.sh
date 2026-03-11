#!/usr/bin/env bash
set -euo pipefail

MIGRATE_VERBOSITY="${MIGRATE_VERBOSITY:-1}"
CREATE_SUPERUSER_ON_START="${CREATE_SUPERUSER_ON_START:-false}"

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

if [[ "${CREATE_SUPERUSER_ON_START}" == "true" ]]; then
  if [[ -z "${DJANGO_SUPERUSER_USERNAME:-}" || -z "${DJANGO_SUPERUSER_EMAIL:-}" || -z "${DJANGO_SUPERUSER_PASSWORD:-}" ]]; then
    echo "CREATE_SUPERUSER_ON_START=true but missing one or more DJANGO_SUPERUSER_* env vars."
    exit 1
  fi
  echo "Ensuring bootstrap admin user exists..."
  python manage.py createsuperuser --noinput || true
fi

echo "Migrations completed."
