#!/usr/bin/env bash
set -euo pipefail

OUTPUT="${1:-docs/openapi/openapi.yaml}"
FORMAT="${2:-yaml}"
case "$OUTPUT" in
  *.json) FORMAT="openapi-json" ;;
  *.yaml|*.yml) FORMAT="openapi" ;;
esac

mkdir -p "$(dirname "$OUTPUT")"

echo "Exporting OpenAPI schema to $OUTPUT..."
DJANGO_SETTINGS_MODULE=config.settings.local \
    uv run python manage.py spectacular --color --format "$FORMAT" --file "$OUTPUT"

echo "Done: $OUTPUT"
