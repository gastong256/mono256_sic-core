# ADR 0001: Record Architecture Decisions

**Status:** Accepted
**Date:** 2024-01-01

## Context

We need a structured way to document significant architectural decisions made over the lifetime of this project so that future contributors can understand the rationale without needing to reconstruct it from git history or conversation.

## Decision

We will use Architecture Decision Records (ADRs) as described by Michael Nygard. Each ADR is a short document in `docs/adr/` capturing the context, the decision, and the consequences.

## Consequences

- Each consequential decision has a matching ADR.
- ADRs are numbered sequentially and never deleted; outdated ones are marked **Superseded**.
- Reviewers are encouraged to reference relevant ADRs in PRs when changing related behaviour.
