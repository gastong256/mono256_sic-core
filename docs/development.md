# Development Guide

This document is the short, practical guide for working on the project locally.

## Supported Local Modes

Use one or both of:

- local Python environment via `uv`
- Docker Compose for dependencies and production-like checks

## Recommended Local Setup

```bash
cp .env.example .env
docker compose up -d postgres
uv sync
make migrate
uv run python manage.py load_chart_of_accounts
make run
```

## Common Commands

- `make run`
- `make test`
- `make lint`
- `make format`
- `make typecheck`
- `make migrate`
- `make export-schema`
- `make check-schema`
- `make check-prod-settings`

## Working Conventions

- put write-side business logic in `services.py`
- put read-side query logic in `selectors.py`
- keep views thin
- preserve immutable accounting behavior
- prefer explicit tests for business rules

## Docker and `.venv`

Be careful when mixing host Python tooling and container-managed environments.

Recommended practice:

- use `.venv` on the host for local development
- use containers mainly for dependencies, CI-like checks and production-like runs
- avoid workflows that rewrite the host `.venv` from inside containers

## Schema and Contract Discipline

Before merging backend changes that affect consumers:

- update serializers
- update tests
- update OpenAPI when HTTP contracts changed
- update docs when the functional contract changed

## Demo Workflow

For demo imports:

- validate the payload first
- prefer canonical demo JSON shape
- use one-shot bootstrap flags only when needed
- switch them off after the import completes
