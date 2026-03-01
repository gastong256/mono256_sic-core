# SIC API

> Implementation of accounting system based in hordak and following SIC (Andrisani) definitions.

**Owner:** gastong256

---

## Table of Contents

- [Using This Template](#using-this-template)
- [Quickstart](#quickstart)
- [Local Dev Workflow](#local-dev-workflow)
- [API Docs](#api-docs)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Observability](#observability)
- [Multi-tenancy](#multi-tenancy)
- [OpenTelemetry](#opentelemetry)
- [Releases & Conventional Commits](#releases--conventional-commits)
- [Contributing](#contributing)

---

## Using This Template

1. Click **"Use this template"** on GitHub to create a new repository.
2. Clone your new repository.
3. Run the bootstrap script:

```bash
make init
```

`make init` prompts for project details, replaces all placeholders, renames files, installs dependencies, and sets up pre-commit hooks. After it completes the project is immediately runnable.

---

## Quickstart

**Prerequisites:** Python 3.12+, [uv](https://docs.astral.sh/uv/), Docker + Docker Compose.

```bash
# 1. Start the database
docker compose up -d postgres

# 2. Apply migrations
make migrate

# 3. Run the dev server
make run
```

The API is now available at `http://localhost:8000`.

```bash
# Liveness check
curl http://localhost:8000/healthz

# Readiness check
curl http://localhost:8000/readyz

# Ping
curl http://localhost:8000/api/v1/ping

# Create an item
curl -s -X POST http://localhost:8000/api/v1/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Widget", "description": "A useful widget."}' | python3 -m json.tool

# Retrieve an item (replace <id> with the UUID from above)
curl http://localhost:8000/api/v1/items/<id>
```

---

## Local Dev Workflow

```bash
make lint          # ruff linter
make format        # black formatter
make typecheck     # pyright
make test          # pytest
make test-cov      # pytest + coverage report
make shell         # Django shell
make migrate       # apply migrations
make makemigrations ARGS="example"  # create migrations for an app
make pre-commit    # run all pre-commit hooks
```

**Adding a new app:**

```bash
uv run python manage.py startapp myapp apps/myapp
```

Follow the pattern in `apps/example/` — add `services.py`, `selectors.py`, `api/`.

---

## API Docs

| URL | Description |
|-----|-------------|
| `/api/openapi.json` | OpenAPI 3.1 schema |
| `/api/docs` | Swagger UI |
| `/api/redoc` | Redoc |

The Postman collection and environment are in `postman/`.

---

## Project Structure

```
apps/               Bounded-context Django apps
  example/          Reference implementation — copy this pattern for new apps
    api/            HTTP layer: serializers, views, urls
    models.py       Data model
    services.py     Write-side business logic
    selectors.py    Read-side query logic
config/             Django project (not an app)
  middleware/       RequestID + Tenant middleware
  settings/         base / local / test / prod
  context.py        ContextVars: request_id, tenant_id
  logging.py        structlog configuration
  otel.py           Optional OpenTelemetry setup
  exceptions.py     DRF custom exception handler
docs/adr/           Architecture Decision Records
tests/              Top-level pytest suite
scripts/            Tooling scripts
postman/            Postman collection + environment
```

---

## Configuration

All configuration is environment-based (12-factor). Copy `.env.example` to `.env` and adjust values.

`DJANGO_SETTINGS_MODULE` selects the settings file:

| Value | Use |
|-------|-----|
| `config.settings.local` | Local development (default) |
| `config.settings.test` | Test runner (set in `pyproject.toml`) |
| `config.settings.prod` | Production |

See `.env.example` for all supported variables.

---

## Observability

See [docs/observability.md](docs/observability.md) for full details.

- **Logs**: JSON to stdout (structlog). Every record includes `request_id` and `tenant_id`.
- **Request ID**: `X-Request-ID` header, auto-generated if missing, echoed in response.
- **Health**: `GET /healthz` (liveness), `GET /readyz` (readiness + DB check).

---

## Multi-tenancy

See [ADR 0002](docs/adr/0002-multitenancy-strategy.md) for the full strategy.

- Send `X-Tenant-ID: my-tenant` in request headers; defaults to `"public"`.
- `tenant_id` appears in all log records automatically.
- No data-layer isolation by default — extend `services.py` and querysets as needed.

---

## OpenTelemetry

OTel is disabled by default with zero overhead when off. To enable:

```bash
uv sync --extra otel

export OTEL_ENABLED=true
export OTEL_SERVICE_NAME=sic_core
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

---

## Releases & Conventional Commits

Releases are automated via [python-semantic-release](https://python-semantic-release.readthedocs.io/) on every merge to `main`.

| Commit prefix | Version bump |
|---------------|-------------|
| `fix:` | patch (0.0.x) |
| `feat:` | minor (0.x.0) |
| `feat!:` / `BREAKING CHANGE:` | major (x.0.0) |
| `chore:`, `docs:`, `test:`, `refactor:` | no release |

Examples:

```
feat: add user authentication endpoint
fix: correct pagination off-by-one error
feat!: remove legacy v0 API endpoints
```

---

## Contributing

1. Branch from `main`: `git checkout -b feat/my-feature`
2. Follow the [service layer pattern](docs/adr/0003-service-layer-pattern.md).
3. Add tests — `make test` must pass.
4. Use Conventional Commits.
5. Open a PR against `main`.
