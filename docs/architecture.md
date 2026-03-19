# Architecture Overview

This document summarizes the current backend architecture at a high level.

## Purpose

SIC is a backend-first educational accounting system designed to:

- simulate an accounting workflow for secondary education
- preserve accounting correctness as the main invariant
- remain simple enough to evolve incrementally

## Supported Environments

The project currently treats these environments as supported:

- local development with `uv`
- local integration and dependency runs with Docker Compose
- production deployment on Render

## Main Building Blocks

The codebase is organized by bounded context:

- `apps/authentication`
- `apps/users`
- `apps/companies`
- `apps/accounts`
- `apps/journal`
- `apps/reports`
- `apps/closing`
- `apps/courses`

Cross-cutting configuration lives in:

- `config/`
- `docs/`
- workflow and deployment files in `.github/`

## Core Architectural Rules

The project follows the services + selectors pattern documented in:

- [docs/adr/0003-service-layer-pattern.md](/home/gastong256/projects/mono256_sic-core/docs/adr/0003-service-layer-pattern.md)

Practical consequences:

- views orchestrate only
- serializers validate shape and present output
- services perform write-side business logic
- selectors perform read/query logic
- accounting truth comes from journal entries

## Accounting Source of Truth

The main accounting truth is the journal layer:

- transactions
- transaction legs
- immutable posting semantics
- reversals instead of destructive edits

Everything else derives from that truth:

- company opening state
- journal book
- ledger
- trial balance
- closing
- snapshots

## Domain Flow

At a high level:

1. a company is created
2. an opening entry initializes accounting activity
3. users create manual journal entries
4. reports derive from those entries
5. closing produces adjustment, result-closing, patrimonial-closing and reopening entries
6. immutable snapshots preserve the closed exercise state

## Logical Exercises

The system currently models fiscal periods as inferred logical exercises, not as a formal persisted `Exercise` entity.

Logical exercise boundaries are inferred from:

- `OPENING`
- `REOPENING`
- `PATRIMONIAL_CLOSING`

This keeps the core simpler while still enabling:

- exercise-aware reports
- closing snapshots
- navigation across closed and open periods

## Reporting Model

The reporting layer currently exposes:

- journal book
- ledger
- trial balance

These reports are exercise-aware and reuse shared metadata about:

- requested range
- effective exercise range
- visible range

The balance sheet and income statement currently exist inside the closing flow and snapshots, not yet as standalone general-purpose reports.

## Cache Strategy

Caching is an optimization layer, not the source of truth.

Current behavior:

- Redis-backed shared cache in production
- safe fallback behavior when Redis is unavailable
- versioned invalidation for charts, visibility and reports
- report caching aligned with logical exercise resolution

## Demo Strategy

Demo companies are first-class operational assets for teaching and onboarding.

Current rules:

- imported from a canonical JSON shape
- content-addressed by SHA-256
- read-only after import
- globally publishable/unpublishable
- suitable for classroom and product smoke validation

## Operations Boundary

Production operations are intentionally kept lean inside this repo.

The project also relies on an external companion ops repository:

- `mono256_sic-ops`
- `https://github.com/gastong256/mono256_sic-ops`

That repository handles automation such as:

- backups
- keep-alive / uptime support
- alerting
- weekly operational reporting

This repo documents application behavior, while `mono256_sic-ops` handles operational automation and can evolve independently.
