# Operations Runbook

This document defines the minimum operational procedures for running SIC in production.

Operational automation that lives outside this repository is currently tracked in:

- `mono256_sic-ops`
- `https://github.com/gastong256/mono256_sic-ops`

This runbook focuses on application/runtime behavior for `mono256_sic-core`.

## 1. Runtime Prerequisites

- A PostgreSQL instance reachable by `DATABASE_URL`.
- A Redis instance reachable by `REDIS_URL`.
- Production currently uses Upstash Redis for the shared cache (`sic-core-redis`).
- Environment variables loaded from a secret store (never from committed files).
- `DJANGO_SETTINGS_MODULE=config.settings.prod`.

## 2. Required Environment Variables

At minimum:

- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `DATABASE_URL`
- `REDIS_URL`
- For Upstash, use the TLS URL provided by the service, typically `rediss://default:PASSWORD@ENDPOINT:PORT`
- `CSRF_TRUSTED_ORIGINS`

Recommended:

- `LOG_LEVEL=INFO`
- `JSON_LOGS=true`
- `WEB_CONCURRENCY=2` (adjust by CPU)
- `DB_CONN_MAX_AGE=60`
- `DB_CONN_HEALTH_CHECKS=true`
- `DB_CONNECT_TIMEOUT=5`
- `ACCOUNT_CHART_CACHE_TIMEOUT=300`
- `ACCOUNT_VISIBILITY_CACHE_TIMEOUT=300`
- `REPORT_CACHE_TIMEOUT=120`
- `REGISTRATION_CONFIG_CACHE_TIMEOUT=300`
- `GUNICORN_ACCESS_LOG_PROD=false` (avoid duplicate request logging)
- `RUN_MIGRATIONS_ON_START=true` (useful for platforms without pre-deploy hooks)
- `COLLECTSTATIC_ON_MIGRATE=true`
- `LOAD_CHART_ON_START=false` (set `true` only for initial chart bootstrap)
- `LOAD_DEMO_ON_START=false` (set `true` only for a one-shot demo bootstrap)
- `DEMO_IMPORT_PROVIDER=r2` (`r2`, `url`, or `file`)
- `DEMO_IMPORT_R2_BASE_URL=` (required when provider is `r2`)
- `DEMO_IMPORT_KEY=demo.json` (defaults to `demo.json`)
- `DEMO_IMPORT_URL=` (required when provider is `url`)
- `DEMO_IMPORT_FILE=` (required when provider is `file`)
- `DEMO_OWNER_USERNAME=demo_owner`
- `DEMO_PUBLISH_ON_IMPORT=true`

## 3. Deployment Procedure

1. Build/update image:
   ```bash
   docker build -t sic_core:prod .
   ```
2. Start infra + migration gate + web:
   ```bash
   make docker-up-prod
   ```
3. Watch startup:
   ```bash
   make docker-logs-prod
   ```
4. Verify readiness:
   - `GET /healthz` returns `200`.
   - `GET /readyz` returns:
     - `200` with `"status": "ok"` for fully healthy state
     - `200` with `"status": "degraded"` when DB is healthy but Redis fallback is active
     - `503` with `"status": "unavailable"` when DB is unavailable
   - When moving or rotating Redis infrastructure, verify `GET /readyz` reports `"redis": true`
5. Verify OpenAPI/docs:
   - `GET /api/docs` loads.

`web` is configured to wait for the one-shot `migrate` service to complete successfully.

## 4. Migration Policy

- All schema changes must be applied through Django migrations.
- Never run app containers with pending migrations.
- If your platform does not support pre-deploy commands (for example, Render Free),
  keep `RUN_MIGRATIONS_ON_START=true` so startup executes `migrate` + `collectstatic`.
- Pre-deploy should run `collectstatic` so `/static/` is materialized in the container.
- For first bootstrap only, optionally set:
  - `LOAD_CHART_ON_START_PROD=true`
- For a one-shot demo bootstrap, optionally set:
  - `LOAD_DEMO_ON_START_PROD=true`
  - `DEMO_IMPORT_PROVIDER_PROD=r2`
  - `DEMO_IMPORT_R2_BASE_URL_PROD=https://pub.example.r2.dev`
  - `DEMO_IMPORT_KEY_PROD=demo.json`
- Keep `LOAD_CHART_ON_START_PROD=false` for normal deployments.
- Keep `LOAD_DEMO_ON_START_PROD=false` for normal deployments.

## 4.1 Demo Import Procedure

Recommended flow:

1. Upload the official demo JSON to the chosen source.
2. Set the import env vars for one deploy only.
3. Deploy and watch the `migrate` service logs.
4. Confirm the import result:
   - a new demo is created when the payload SHA-256 is new
   - import is skipped when an identical payload was already imported
5. Turn `LOAD_DEMO_ON_START_PROD` back to `false`.
6. Use the admin publication endpoint to publish/unpublish demos without deleting them.

Important behaviors:

- Demo imports are content-addressed by `demo_content_sha256`.
- The imported company becomes `is_demo=true` and `is_read_only=true`.
- Demo slugs are derived from the payload name and versioned on collisions (`slug`, `slug-v2`, `slug-v3`, ...).
- Publication is global and separate from course-level demo visibility.
- The import command only accepts the canonical `opening_entry + logical_exercises` format.
- If a demo payload is structurally invalid or breaks accounting/logical-exercise rules, the import is skipped with a warning and the deploy continues.

Manual migration (outside compose) if needed:

```bash
make migrate-prod
```

## 5. Rollback Strategy

If deploy introduces runtime errors:

1. Roll back application image to previous version.
2. If migration was backward-compatible, keep DB as is.
3. If migration requires DB rollback:
   - execute explicit reverse migration only if tested.
   - restore from backup if reverse migration is unsafe.

Do not perform ad-hoc schema edits directly on production DB.

## 6. Backup and Restore (Database)

Minimum policy:

- Daily logical backup (`pg_dump`) plus retention policy.
- Backup before every release that includes migrations.
- Periodic restore drill in non-production.

Restore checklist:

1. Provision clean DB.
2. Restore dump.
3. Deploy matching app version.
4. Run `GET /readyz` and smoke-test critical endpoints.

## 7. Monitoring and Alerts (Minimum)

Monitor at least:

- Availability: `/healthz`, `/readyz`.
- HTTP 5xx rate.
- Request latency (`duration_ms`) and `slow_request` events.
- DB connectivity failures.
- Redis connectivity failures and prolonged `readyz.status=degraded`.
- Container restarts/crashes.

Use `request_id` in logs to trace incidents end-to-end.

## 8. Performance Validation

Before releasing high-impact changes, run:

1. Load smoke profile against representative endpoints:
   ```bash
   ./scripts/load_profile.sh "http://localhost:8000/api/v1/companies/1/journal/?page=1" 200 20
   ```
2. Query-plan inspection for reporting/list endpoints:
   ```bash
   ./scripts/db_explain.sh 1
   ```
3. Capture and record at least:
   - p95 latency
   - success rate
   - queries/request (from explain + app logs)
   - worker memory (RSS) under sustained load

## 9. Security Operations

- Rotate `DJANGO_SECRET_KEY` and DB credentials under controlled maintenance windows.
- Keep `DEBUG=false` in production.
- Enforce HTTPS at the edge and keep secure cookie settings.
- Restrict admin users (`role=admin`, `is_staff=true`) to trusted operators only.

## 10. Incident Response Quick Guide

1. Check service status:
   - `GET /healthz`, `GET /readyz`.
2. Inspect recent logs for:
   - `request_failed`
   - 5xx spikes
   - DB/Redis connection errors
3. If `readyz.status=degraded`, prioritize cache/backend dependency recovery while confirming that critical flows still work.
4. Identify affected scope:
   - single endpoint / single tenant / global.
5. Mitigate:
   - rollback app image or disable recent feature via config.
6. Recover:
   - verify readiness and critical user flows.
7. Postmortem:
   - document root cause and action items.
