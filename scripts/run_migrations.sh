#!/usr/bin/env bash
set -euo pipefail

MIGRATE_VERBOSITY="${MIGRATE_VERBOSITY:-1}"
CREATE_SUPERUSER_ON_START="${CREATE_SUPERUSER_ON_START:-false}"
LOAD_CHART_ON_START="${LOAD_CHART_ON_START:-false}"
LOAD_DEMO_ON_START="${LOAD_DEMO_ON_START:-false}"

echo "Applying database migrations..."
python manage.py migrate --noinput --verbosity "${MIGRATE_VERBOSITY}"

if [[ "${LOAD_CHART_ON_START}" == "true" ]]; then
  echo "Loading base chart of accounts..."
  python manage.py load_chart_of_accounts
elif [[ "${LOAD_CHART_ON_START}" != "false" ]]; then
  echo "Invalid LOAD_CHART_ON_START value: ${LOAD_CHART_ON_START}. Use true/false."
  exit 1
fi

if [[ "${LOAD_DEMO_ON_START}" == "true" ]]; then
  DEMO_IMPORT_PROVIDER="${DEMO_IMPORT_PROVIDER:-r2}"
  DEMO_OWNER_USERNAME="${DEMO_OWNER_USERNAME:-demo_owner}"
  DEMO_IMPORT_KEY="${DEMO_IMPORT_KEY:-demo.json}"
  DEMO_PUBLISH_ON_IMPORT="${DEMO_PUBLISH_ON_IMPORT:-true}"

  echo "Loading demo company..."
  demo_args=(manage.py load_demo_company --owner-username "${DEMO_OWNER_USERNAME}")

  if [[ "${DEMO_PUBLISH_ON_IMPORT}" == "true" ]]; then
    demo_args+=(--publish)
  elif [[ "${DEMO_PUBLISH_ON_IMPORT}" == "false" ]]; then
    demo_args+=(--no-publish)
  else
    echo "Invalid DEMO_PUBLISH_ON_IMPORT value: ${DEMO_PUBLISH_ON_IMPORT}. Use true/false."
    exit 1
  fi

  case "${DEMO_IMPORT_PROVIDER}" in
    file)
      if [[ -z "${DEMO_IMPORT_FILE:-}" ]]; then
        echo "DEMO_IMPORT_FILE is required when DEMO_IMPORT_PROVIDER=file."
        exit 1
      fi
      demo_args+=(--file "${DEMO_IMPORT_FILE}")
      ;;
    url)
      if [[ -z "${DEMO_IMPORT_URL:-}" ]]; then
        echo "DEMO_IMPORT_URL is required when DEMO_IMPORT_PROVIDER=url."
        exit 1
      fi
      demo_args+=(--url "${DEMO_IMPORT_URL}")
      ;;
    r2)
      if [[ -z "${DEMO_IMPORT_R2_BASE_URL:-}" ]]; then
        echo "DEMO_IMPORT_R2_BASE_URL is required when DEMO_IMPORT_PROVIDER=r2."
        exit 1
      fi
      demo_args+=(--r2-base-url "${DEMO_IMPORT_R2_BASE_URL}" --r2-key "${DEMO_IMPORT_KEY}")
      ;;
    *)
      echo "Invalid DEMO_IMPORT_PROVIDER value: ${DEMO_IMPORT_PROVIDER}. Use file/url/r2."
      exit 1
      ;;
  esac

  python "${demo_args[@]}"
elif [[ "${LOAD_DEMO_ON_START}" != "false" ]]; then
  echo "Invalid LOAD_DEMO_ON_START value: ${LOAD_DEMO_ON_START}. Use true/false."
  exit 1
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
