# Accounting Rules

This document captures the main accounting invariants enforced by the current backend.

It is intentionally short and operational.

## Core Principle

Journal entries are the accounting source of truth.

Reports, closing behavior and snapshots derive from journal state. The system should not maintain competing accounting truths.

## Opening Rules

- A company starts accounting activity through an opening entry.
- Opening validates allowed patrimonial account groups.
- Opening creates the initial accounting base for the first logical exercise.
- Opening is not treated as a regular manual journal flow.

## Journal Entry Rules

- Manual entries must balance exactly.
- Lines must use positive amounts.
- Debit and credit semantics must be valid.
- Only company-owned movement accounts can be used for posting.
- Existing journal truth is not edited destructively.
- When correction is needed, reversal-style behavior is preferred.

## Account Structure Rules

The current chart model uses:

- level 0: rubros
- level 1: colectivas
- level 2: company movement accounts

Global chart levels are shared and read-only. Company movement accounts are the operational posting surface.

## Reporting Rules

Current general reports:

- journal book
- ledger
- trial balance

These reports:

- derive from journal truth
- resolve against logical exercises
- can explain the requested range versus the effective accounting window used

## Logical Exercise Rules

The system does not yet persist a formal `Exercise` model.

Instead, it infers logical exercises from special accounting entries:

- `OPENING`
- `REOPENING`
- `PATRIMONIAL_CLOSING`

Rules:

- the first exercise starts with `OPENING`
- subsequent exercises start with `REOPENING`
- an exercise ends with `PATRIMONIAL_CLOSING`
- exercise chains must remain canonical and non-overlapping

## Closing Rules

The current closing flow supports:

- preview
- execution
- immutable snapshot generation

At execution time, the system may produce:

- adjustment entries
- result-closing entries
- patrimonial-closing entry
- reopening entry

Current built-in adjustment depth is intentionally narrow and focused on:

- cash arqueo
- inventory differences

## Snapshot Rules

Closing snapshots are immutable.

They exist to preserve the formal closed state of an exercise, including:

- closed balances
- balance sheet payload
- income statement payload

Snapshots are not a replacement for the journal. They are a frozen accounting output of a confirmed close.

## Demo Company Rules

Imported demos are:

- `is_demo=true`
- `is_read_only=true`

They are designed for:

- teaching
- onboarding
- smoke validation

They are not writable accounting sandboxes after import.

## Design Constraint

Whenever a new feature is added, it should answer this question clearly:

"Does this feature preserve the journal as the accounting source of truth?"

If the answer is unclear, the design should be reconsidered before implementation.
