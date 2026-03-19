# Frontend Integration Guide

This document is a generic guide for frontend consumers of the SIC API.

It is not tied to a specific frontend repository.

## General Integration Rule

Treat the backend as the accounting source of truth.

Frontend code should:

- render backend accounting outputs
- respect backend ranges and exercise semantics
- avoid re-implementing accounting logic that already exists in the API

## Main Functional Areas

The current frontend-relevant backend areas are:

- authentication
- companies
- accounts
- journal posting
- reports
- closing
- demo visibility/publication

## Report Consumption

Current accounting reports expose metadata that helps UI avoid guessing:

- requested range
- effective exercise range
- visible range
- active exercise
- previous exercises

Frontend consumers should use that metadata for:

- page titles
- breadcrumbs
- date range indicators
- exercise navigation

## Closing Consumption

The closing flow currently provides:

- state
- preview
- execute
- immutable snapshots

Practical integration rules:

- preview is mutable and exploratory
- execute is the formal confirmation step
- snapshots represent frozen accounting truth for closed exercises
- snapshot-based balance sheet and income statement are formal closed outputs, not arbitrary-date dynamic reports

## Demo Consumption

Imported demos:

- may be published or unpublished
- are read-only
- can coexist by version/slug

Frontend implications:

- do not offer mutation flows on read-only demos
- surface publication-aware visibility correctly
- distinguish demo exploration from writable student/company workflows

## Error Handling

Frontend consumers should preserve backend semantics for:

- validation errors
- permission errors
- read-only demo conflicts
- accounting conflicts

Avoid translating all failures into a generic UI error state.

## Caching Guidance

Frontend caches should align with backend semantics:

- use stable query keys by company, report and relevant date/filter scope
- invalidate on accounting mutations
- treat snapshots as highly cacheable
- treat preview responses as short-lived
- avoid inferring effective accounting ranges from raw inputs alone

## Recommended Documentation Pairing

This document should be read together with:

- [docs/accounting-rules.md](/home/gastong256/projects/mono256_sic-core/docs/accounting-rules.md)
- [docs/openapi/openapi.yaml](/home/gastong256/projects/mono256_sic-core/docs/openapi/openapi.yaml)
- [docs/architecture.md](/home/gastong256/projects/mono256_sic-core/docs/architecture.md)
