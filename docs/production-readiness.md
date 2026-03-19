# Production Readiness Notes

This document captures the current operational focus for the first real production stage.

## Current Rollout Context

The near-term production expectation is an initial usage band of roughly:

- 30 to 50 users
- with real concurrent usage

This stage is not about maximum scale yet. It is about validating the current core safely in real usage.

## Immediate Priorities

Based on the current product plan, the next production-facing priorities are:

1. adjustments and operational metrics for the current core
2. commercial/accounting documents
3. IVA

## What To Watch In The First Weeks

Application signals:

- `readyz` status
- DB availability
- Redis availability or degraded fallback state
- request latency
- slow request frequency
- 5xx rate
- startup stability during deploys

Accounting signals:

- opening flow reliability
- journal posting correctness under real usage
- report generation latency
- closing preview and execute reliability
- demo visibility and read-only behavior

## Companion Ops Layer

This repository is not the whole operational picture.

There is also a companion ops repository used for automation such as:

- database backups
- keep-alive and health automation
- redeploy attempts when the app is not healthy
- weekly operational reports
- Discord alerts
- free-tier limit monitoring

This split is intentional:

- this repo documents application behavior
- the ops repo handles environment automation

## First-Stage Success Criteria

This phase should be considered healthy when:

- production remains stable under expected classroom usage
- reports remain responsive enough for normal teaching flows
- closing continues to work without accounting regressions
- deploys are predictable
- backups and operational alerts stay trustworthy

## Near-Term Documentation Rule

During this first production phase, changes should update documentation whenever they affect:

- deployment behavior
- startup flags
- report contracts
- closing behavior
- operational assumptions
