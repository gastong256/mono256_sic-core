# Contributing

Thank you for your interest in the project.

## Current Contribution Policy

This repository is public, but it is currently maintained as a personal project.

At this stage:

- external pull requests are not being actively accepted
- the maintainer remains the main integration gate for product and architectural changes

The repository is public for:

- visibility
- reference
- documentation
- technical collaboration context

## Internal Contribution Expectations

Changes merged into the project should:

- preserve the accounting core as the source of truth
- follow the services + selectors pattern
- keep HTTP contracts documented
- include tests when behavior changes
- update docs when user-facing or operational behavior changes

## Before Merging

At minimum:

- `make lint`
- `make typecheck`
- `make test`
- `make check-schema`
- `make check-prod-settings`

should pass when relevant to the change.

## Commit and Release Style

The project follows:

- Conventional Commits
- semantic versioning
- semantic-release driven versioning

See:

- [docs/release-process.md](/home/gastong256/projects/mono256_sic-core/docs/release-process.md)
