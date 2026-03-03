# SIC API

> Sistema de Información Contable — an educational double-entry accounting system
> based on [django-hordak](https://github.com/adamchainz/django-hordak) and the
> SIC 1 - Angrisani textbook (Argentine accounting).

**Owner:** gastong256

---

## Table of Contents

- [Overview](#overview)
- [Roles and Permissions](#roles-and-permissions)
- [Quickstart](#quickstart)
- [Installation and Configuration](#installation-and-configuration)
- [Loading the Chart of Accounts](#loading-the-chart-of-accounts)
- [API Reference](#api-reference)
  - [Authentication](#authentication)
  - [Companies](#companies)
  - [Accounts](#accounts)
- [Project Structure](#project-structure)
- [Local Dev Workflow](#local-dev-workflow)
- [Observability](#observability)
- [Operations Runbook](#operations-runbook)
- [OpenTelemetry](#opentelemetry)
- [Releases and Conventional Commits](#releases-and-conventional-commits)

---

## Overview

SIC is a backend-only Django REST API that simulates an accounting studio environment
for high school students. Each student can manage one or more fictional companies and
practice double-entry bookkeeping using a predefined Argentine chart of accounts.

**Key design decisions:**

| Concern | Approach |
|---------|----------|
| Double-entry bookkeeping | `django-hordak` (MPTTModel) |
| Authentication | JWT via `djangorestframework-simplejwt` |
| Account tree | 3 levels: rubros (L0) → colectivas (L1) → subcuentas (L2) |
| Currency | Argentine Peso (ARS) |
| Permissions | Role-based (`admin`, `teacher`, `student`) |

---

## Roles and Permissions

| Role | Identification | Access |
|------|----------------|--------|
| **Admin** | `role=admin` + `is_staff=True` | Full API + Django Admin + role management |
| **Teacher** | `role=teacher` | Course management, student supervision, accounting operations |
| **Student** | `role=student` | Accounting operations on own scope |

### Detailed permission rules

- **Companies:** Students see/manage own companies. Teachers see own + companies of students enrolled in their courses. Admin sees all.
- **Level-0/1 accounts (rubros, colectivas):** Global, read-only via API. Teachers can apply show/hide overrides for their students.
- **Level-2 accounts (subcuentas):** Students create/edit/delete on allowed companies. Teachers/admin can operate on supervised scope.
- **Deleting accounts:** Blocked (409 Conflict) if the account has transaction legs in hordak.
- **Courses:** Teachers/admin can create courses and enroll students (one course per student).

---

## Quickstart

**Prerequisites:** Python 3.12+, [uv](https://docs.astral.sh/uv/), Docker + Docker Compose.

```bash
# 1. Start the PostgreSQL database
docker compose up -d postgres

# 2. Install dependencies
uv sync

# 3. Apply migrations (hordak, users, companies, …)
make migrate

# 4. Load the base chart of accounts
uv run python manage.py load_chart_of_accounts

# 5. Create a superuser (teacher)
uv run python manage.py createsuperuser

# 6. Run the dev server
make run
```

The API is now available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/api/docs`

---

## Installation and Configuration

### Environment variables

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

Required variables:

| Variable | Example | Description |
|----------|---------|-------------|
| `DJANGO_SETTINGS_MODULE` | `config.settings.local` | Settings file to use |
| `DJANGO_SECRET_KEY` | `change-me` | Django secret key |
| `DATABASE_URL` | `postgres://postgres:postgres@localhost:5432/sic_core` | PostgreSQL connection string |

> **Note:** `django-hordak` requires PostgreSQL. SQLite is not supported because
> hordak uses a PostgreSQL trigger to compute `full_code` on the Account model.

### Settings profiles

| Value | Use |
|-------|-----|
| `config.settings.local` | Local development (debug on, JSON logs off) |
| `config.settings.test` | Test runner (set automatically by `pyproject.toml`) |
| `config.settings.prod` | Production (strict security headers, HTTPS) |

---

## Loading the Chart of Accounts

Run the management command after each fresh database setup:

```bash
uv run python manage.py load_chart_of_accounts
```

The command is **idempotent** — running it multiple times never creates duplicates.

It loads:

| Code | Name | Type |
|------|------|------|
| 1 | ACTIVO | AS (Asset) |
| 1.01 | Caja | — |
| 1.02 | Valores a Depositar | — |
| … (17 colectivas total) | | |
| 2 | PASIVO | LI (Liability) |
| 2.01 | Proveedores | — |
| … (6 colectivas) | | |
| 3 | PATRIMONIO NETO | EQ (Equity) |
| 4 | RESULTADOS NEGATIVOS | EX (Expense) |
| 5 | RESULTADOS POSITIVOS | IN (Income) |

Account codes use the hordak/MPTT local code convention:
- Level-0 root code: `"1"`, `"2"`, … → `full_code = "1"`, `"2"`, …
- Level-1 local code: `".01"`, `".02"`, … → `full_code = "1.01"`, `"1.02"`, …
- Level-2 local code: `".01"`, `".02"`, … → `full_code = "1.04.01"`, `"2.01.03"`, …

---

## API Reference

Base URL: `http://localhost:8000/api/v1`

Interactive docs: `GET /api/docs` (Swagger UI) or `GET /api/redoc`.
Repository artifact: `docs/openapi/openapi.yaml` (regenerate with `make export-schema`).

---

### Authentication

JWT tokens are required for all SIC endpoints.

#### Student self-registration

```http
POST /api/v1/auth/register/
Content-Type: application/json

{
  "username": "student2",
  "password": "StrongPass123!",
  "password_confirm": "StrongPass123!",
  "registration_code": "ABCDE-12345"
}
```

The registration code rotates globally and is visible to teachers/admins:
- `GET /api/v1/teacher/registration-code/`
- `GET /api/v1/admin/registration-code/`
- `POST /api/v1/admin/registration-code/rotate/` (admin only)

#### Obtain token

```http
POST /api/v1/auth/token/
Content-Type: application/json

{
  "username": "student1",
  "password": "password123"
}
```

Response `200 OK`:

```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Refresh token

```http
POST /api/v1/auth/token/refresh/
Content-Type: application/json

{
  "refresh": "<refresh_token>"
}
```

Response `200 OK`:

```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

Include the access token in all subsequent requests:

```http
Authorization: Bearer <access_token>
```

---

### Companies

Students act as an accounting firm and can manage multiple companies.

### Courses and Teacher Supervision

- `GET/POST /api/v1/courses/`
- `GET/PATCH/DELETE /api/v1/courses/{course_id}/`
- `POST /api/v1/courses/{course_id}/enrollments/`
- `DELETE /api/v1/courses/{course_id}/enrollments/{student_id}/`
- `GET /api/v1/teacher/courses/{course_id}/companies/`
- `GET /api/v1/teacher/courses/{course_id}/journal-entries/`

### Admin Role Management

- `PATCH /api/v1/admin/users/{user_id}/role/`

Body:

```json
{
  "role": "teacher"
}
```

#### List companies

```http
GET /api/v1/companies/
Authorization: Bearer <token>
```

Students see only their own companies. Teachers see all.

Response `200 OK`:

```json
{
  "count": 1,
  "results": [
    {
      "id": 1,
      "name": "Ferretería El Clavo",
      "tax_id": "20-12345678-9",
      "owner_username": "student1",
      "account_count": 3,
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

#### Create company

```http
POST /api/v1/companies/
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Ferretería El Clavo",
  "tax_id": "20-12345678-9"
}
```

Response `201 Created` — same format as list item above.

#### Retrieve company

```http
GET /api/v1/companies/{id}/
Authorization: Bearer <token>
```

Response `200 OK` — same format as list item.

#### Update company

```http
PUT /api/v1/companies/{id}/
PATCH /api/v1/companies/{id}/
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Ferretería El Clavo SRL",
  "tax_id": "30-12345678-9"
}
```

Response `200 OK` — updated company.

#### Delete company

```http
DELETE /api/v1/companies/{id}/
Authorization: Bearer <token>
```

Response `204 No Content`.

---

### Accounts

#### Get global chart of accounts

Returns levels 1 and 2 (global, no company-specific subcuentas).

```http
GET /api/v1/accounts/chart/
Authorization: Bearer <token>
```

Response `200 OK`:

```json
[
  {
    "id": 1,
    "code": "1",
    "name": "ACTIVO",
    "type": "AS",
    "level": 0,
    "is_leaf": false,
    "children": [
      {
        "id": 2,
        "code": "1.01",
        "name": "Caja",
        "type": "AS",
        "level": 1,
        "is_leaf": true,
        "children": []
      },
      {
        "id": 3,
        "code": "1.02",
        "name": "Valores a Depositar",
        "type": "AS",
        "level": 1,
        "is_leaf": true,
        "children": []
      }
    ]
  },
  {
    "id": 19,
    "code": "2",
    "name": "PASIVO",
    "type": "LI",
    "level": 0,
    "is_leaf": false,
    "children": [...]
  }
]
```

#### Get company chart of accounts

Returns levels 1 and 2 (global) plus level-3 subcuentas belonging to the company.

```http
GET /api/v1/accounts/company/{company_id}/
Authorization: Bearer <token>
```

Response `200 OK` — same tree format, with level-2 `children` populated per company.

#### Create level-3 account

```http
POST /api/v1/accounts/company/{company_id}/
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Caja Principal",
  "code": "1.01.01",
  "parent_id": 2
}
```

Field rules:
- `code`: full code in `X.XX.XX` format; must be globally unique in hordak
- `parent_id`: ID of a level-1 (colectiva) account; type and currency are inherited
- Only students who own the company (or teachers) can create accounts

Response `201 Created`:

```json
{
  "id": 42,
  "code": "1.01.01",
  "name": "Caja Principal",
  "type": "AS",
  "level": 2,
  "is_leaf": true,
  "children": []
}
```

Common errors:

| Status | Cause |
|--------|-------|
| `400` | Invalid code format, duplicate code, parent not level-1 |
| `403` | Student accessing another student's company |
| `404` | Company or parent account not found |

#### Update level-3 account

```http
PATCH /api/v1/accounts/company/{company_id}/{account_id}/
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Caja Chica",
  "code": "1.01.02"
}
```

Both fields are optional, but at least one must be provided.

Response `200 OK` — updated account node.

#### Delete level-3 account

```http
DELETE /api/v1/accounts/company/{company_id}/{account_id}/
Authorization: Bearer <token>
```

Response `204 No Content`.

Error `409 Conflict` — if the account has existing transaction legs in hordak:

```json
{
  "error": {
    "code": "conflict",
    "message": "Cannot delete account with existing transactions. Reverse the transactions first.",
    "detail": null
  }
}
```

---

## Project Structure

```
apps/
  common/             Shared abstract models (TimeStampedModel)
  users/              Custom User model (AbstractUser, no extra fields)
    api/              JWT token endpoints
  companies/          Company, CompanyAccount models + full REST API
    api/              ViewSet, serializers, permissions
    management/
      commands/       load_chart_of_accounts
  accounts/           Wraps hordak.Account — no own DB models
    api/              Chart endpoints, account create/update/delete
  example/            Reference app (ping, items)
config/
  settings/           base / local / test / prod
  middleware/         RequestID + Tenant middleware
  exceptions.py       DRF exception handler + ConflictError (409)
  logging.py          structlog configuration
  otel.py             Optional OpenTelemetry setup
```

---

## Local Dev Workflow

```bash
make lint          # ruff linter
make format        # black formatter
make typecheck     # pyright
make test-db-up    # start postgres dependency for tests
make test          # pytest
make test-cov      # pytest + coverage report
make shell         # Django shell
make migrate       # apply migrations
make pre-commit    # run all pre-commit hooks
```

`make test` runs a DB preflight check and fails fast if PostgreSQL is not reachable.

Load the chart of accounts after a fresh DB:

```bash
uv run python manage.py load_chart_of_accounts
```

## CI Quality Gates

The CI workflow runs these minimum gates on every PR/push:
- Ruff lint (`make lint`)
- Black format check (`make format-check`)
- Pyright type check (`make typecheck`)
- OpenAPI validation (`make check-schema`)
- Django production checks (`make check-prod-settings`)
- Pytest (+ coverage on initialized repo)

## Production-Like Compose Workflow

Use the production compose profile to run PostgreSQL + Redis + migration job + web:

```bash
make docker-up-prod
make docker-logs-prod
```

The `migrate` service runs first and must complete successfully before `web` starts.
Optional bootstrap:
- set `LOAD_BASE_CHART_ON_MIGRATE_PROD=true` to load the base chart after migrations.
- keep it `false` in steady-state deployments.

---

## Observability

- **Logs:** JSON to stdout (structlog). Every record includes `request_id` and `tenant_id`.
- **HTTP access logs:** request method/path/status/duration with `slow_request` threshold alerts.
- **Request ID:** `X-Request-ID` header, auto-generated if missing, echoed in response.
- **Health:** `GET /healthz` (liveness), `GET /readyz` (readiness + DB check).

## Operations Runbook

Operational procedures are documented in:

- `docs/operations.md` (deploy, migration policy, backup/restore, rollback, incident response)

---

## OpenTelemetry

OTel is disabled by default. To enable:

```bash
uv sync --extra otel

export OTEL_ENABLED=true
export OTEL_SERVICE_NAME=sic_core
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

---

## Releases and Conventional Commits

Releases are automated via python-semantic-release on every merge to `main`.

| Commit prefix | Version bump |
|---------------|-------------|
| `fix:` | patch (0.0.x) |
| `feat:` | minor (0.x.0) |
| `feat!:` / `BREAKING CHANGE:` | major (x.0.0) |
| `chore:`, `docs:`, `test:`, `refactor:` | no release |
