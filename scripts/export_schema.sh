#!/usr/bin/env bash
set -euo pipefail

OUTPUT="${1:-openapi.json}"

echo "Exporting OpenAPI schema to $OUTPUT..."
DJANGO_SETTINGS_MODULE=config.settings.local \
    uv run python manage.py spectacular --color --file "$OUTPUT"

echo "Done: $OUTPUT"
