# ADR 0003: Service Layer Pattern

**Status:** Accepted
**Date:** 2024-01-01

## Context

Django encourages putting business logic in models ("fat models") or views ("fat views"). Both approaches make the codebase harder to test in isolation and lead to duplication when the same logic is needed from multiple entry points (REST views, management commands, Celery tasks, etc.).

## Decision

We adopt the **services + selectors** pattern:

- **`services.py`** — write-side operations. Contains all business logic that mutates state: validation beyond serializers, orchestration of multiple model saves, event emission, external calls. Functions are keyword-argument-only to avoid positional confusion. They call `full_clean()` before `save()`.

- **`selectors.py`** — read-side operations. Contains all non-trivial query logic: filtered querysets, annotations, prefetch strategies. Keeps views thin and makes query logic reusable and testable.

- **Views** (`api/views.py`) — orchestration only: deserialize input → call service/selector → serialize output → return response. No ORM access or business logic.

- **Serializers** (`api/serializers.py`) — shape validation and presentation only. Input serializers validate structure; output serializers control the response envelope.

## Consequences

- Each bounded-context app has a predictable file layout.
- Business logic is easily unit-tested without spinning up HTTP.
- Fat views and fat models are prohibited by convention; PRs violating this should be flagged.
- For simple CRUD with no real business logic, a thin service wrapping `Model.objects.create()` is still required as a consistency trade-off.
