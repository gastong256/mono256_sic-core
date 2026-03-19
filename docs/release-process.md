# Release Process

This document summarizes the current release model.

## Current Release Style

The project uses:

- semantic versioning
- semantic-release
- CI validation before release
- Render deploy hook triggered by tags/releases

Relevant workflow files:

- [/.github/workflows/ci.yml](/home/gastong256/projects/mono256_sic-core/.github/workflows/ci.yml)
- [/.github/workflows/release.yml](/home/gastong256/projects/mono256_sic-core/.github/workflows/release.yml)
- [/.github/workflows/deploy-render-on-tag.yml](/home/gastong256/projects/mono256_sic-core/.github/workflows/deploy-render-on-tag.yml)

## Current Baseline

Today the project releases through semantic-release on `main` after CI succeeds.

The maintainer may refine the deployment cadence later, for example by moving to a calendar-based release rhythm instead of deploying every release immediately.

## Minimum Release Checklist

Before a release:

- CI is green
- schema changes are migrated
- OpenAPI is current when contracts changed
- docs are updated when behavior changed
- production-impacting environment variables are known

## Deployment Note

Tag-driven deploys currently trigger Render through a deploy hook.

For production changes with one-shot startup actions:

- chart bootstrap flags should only be enabled when needed
- demo import flags should only be enabled when needed

After the deploy succeeds, those flags should return to their safe default state.
