# Operations Runbook

This document defines the minimum operational procedures for running SIC in production.

## 1. Runtime Prerequisites

- A PostgreSQL instance reachable by `DATABASE_URL`.
- A Redis instance reachable by `REDIS_URL`.
- Environment variables loaded from a secret store (never from committed files).
- `DJANGO_SETTINGS_MODULE=config.settings.prod`.

## 2. Required Environment Variables

At minimum:

- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `DATABASE_URL`
- `REDIS_URL`
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
- `REGISTRATION_CONFIG_CACHE_TIMEOUT=300`
- `GUNICORN_ACCESS_LOG_PROD=false` (avoid duplicate request logging)
- `RUN_MIGRATIONS_ON_START=true` (useful for platforms without pre-deploy hooks)
- `COLLECTSTATIC_ON_MIGRATE=true`
- `LOAD_CHART_ON_START=false` (set `true` only for initial chart bootstrap)

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
   - `GET /readyz` returns `200`.
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
- Keep `LOAD_CHART_ON_START_PROD=false` for normal deployments.

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
3. Identify affected scope:
   - single endpoint / single tenant / global.
4. Mitigate:
   - rollback app image or disable recent feature via config.
5. Recover:
   - verify readiness and critical user flows.
6. Postmortem:
   - document root cause and action items.
