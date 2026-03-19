# Testing Guide

This document defines the current testing expectations for the project.

## Goal

Keep accounting behavior safe while the product evolves.

## Current Test Layers

The project currently relies on:

- service-level tests for business rules
- API tests for contracts and permissions
- report tests for derived accounting outputs
- import tests for demo loading behavior

## Primary Commands

```bash
make test
make test-cov
make lint
make format-check
make typecheck
make check-schema
make check-prod-settings
```

## Database Expectations

Tests run against PostgreSQL-backed behavior. This matters because the project depends on `django-hordak`, which requires PostgreSQL semantics.

For local work:

- use Docker Compose to provide Postgres when needed
- avoid assuming SQLite compatibility

## What Must Be Tested

Changes should include tests whenever they alter:

- accounting posting rules
- opening behavior
- logical exercise resolution
- report contracts
- closing behavior
- demo import validation
- permissions or visibility

## OpenAPI and Contract Safety

If an HTTP response or request shape changes:

- update schema generation
- update API tests
- update docs

## Release Safety

At minimum, release candidates should pass:

- lint
- format check
- typecheck
- schema validation
- production settings check
- full test suite
