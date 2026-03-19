# Product Backlog

This backlog captures the next functional steps to evolve SIC from a strong accounting core into a fuller SIC 1-aligned educational system.

The stories below are intentionally written in a concise, sprint-ready style.

## Product Goal

Evolve the current backend from:

- a strong posting, reporting and closing engine

into:

- a fuller educational accounting platform aligned with SIC 1
- still centered on a clean, auditable accounting core
- without sacrificing simplicity for beginner and intermediate learning paths

## Planning Principles

The backlog should be read with these product rules in mind:

- preserve the current accounting core as the source of truth
- prefer additive features over disruptive rewrites
- keep beginner-friendly scenarios simple
- add pedagogical richness on top of the core, not instead of it
- prioritize features that unlock both teacher value and student practice value
- favor report and workflow reuse across demos, courses and future guided exercises

## Current Baseline

What the project already does well:

- opening entry
- immutable double-entry posting
- journal book
- ledger
- trial balance
- logical exercises
- simplified closing
- patrimonial closing
- reopening
- immutable closing snapshots

What is still missing for stronger SIC 1 alignment:

- standalone financial statements
- legal/accounting books beyond the current reporting trio
- IVA workflow
- broader adjustment workflow
- document-centered accounting flows
- societies and profit distribution
- stronger didactic overlays

## Backlog Structure

The backlog is split into:

- near-term sprint candidates
- enabling work and dependencies
- medium-term roadmap by release band
- longer-term opportunities

## Sprint Candidates

### Epic: Financial Statements

#### Story 1: Standalone Balance Sheet

As a student or teacher, I want to query a balance sheet at a given date so that I can review the patrimonial situation without having to go through the closing workflow.

Acceptance criteria:
- New report endpoint for balance sheet.
- Supports company + date.
- Returns grouped assets, liabilities and equity.
- Includes equation check.
- Works for open and closed exercises.
- Reuses the same accounting semantics already used by logical exercises and closing snapshots.

#### Story 2: Standalone Income Statement

As a student or teacher, I want to query an income statement for a given exercise/date so that I can inspect gains, losses and net result outside the closing flow.

Acceptance criteria:
- New report endpoint for income statement.
- Returns grouped positive and negative results.
- Includes net result.
- Can be consumed independently from closing preview.
- Can explain the effective exercise/range used for calculation.

#### Story 3: Inventory and Balances Book

As a teacher, I want a formal inventory and balances report so that students can understand the legal and accounting bridge between inventory, statements and closing.

Acceptance criteria:
- Inventory snapshot grouped by patrimonial rubros.
- Includes opening inventory and closing inventory perspective.
- Can be exported.
- Fits the current logical exercise model instead of bypassing it.

### Epic: Adjustments

#### Story 4: Advanced Closing Adjustments

As a student, I want more adjustment types before closing so that the simulation aligns better with SIC 1.

Acceptance criteria:
- Support for unpaid expenses.
- Support for accrued income.
- Support for prepaid expenses.
- Support for amortization of fixed assets.
- Support for omitted bank charges.
- Adjustments remain traceable as journal entries or journal drafts.

#### Story 5: Debtor Cleansing

As a teacher, I want to reclassify debtors by condition so that students can practice debtor cleansing at year end.

Acceptance criteria:
- Reclassification for:
  - regular debtors
  - late debtors
  - judicial debtors
  - uncollectible debtors
- Visible impact in reports and closing.
- Can be taught as an end-of-period adjustment flow.

### Epic: IVA

#### Story 6: IVA Purchase and Sales Books

As a student, I want IVA purchase and sales books so that I can understand the tax record basis behind IVA accounting.

Acceptance criteria:
- IVA Purchases Book.
- IVA Sales Book.
- Proper treatment of A/B/C cases at report level.
- Compatible with the current chart and manual posting model.

#### Story 7: IVA Monthly Liquidation

As a student, I want the backend to calculate monthly IVA position so that I can understand debit fiscal, credit fiscal and saldo a pagar.

Acceptance criteria:
- Monthly IVA position report.
- Debit fiscal vs credit fiscal.
- Carry-forward if credit exceeds debit.
- Optional journal draft for IVA settlement/payment.
- Does not require replacing the existing journal engine.

### Epic: Commercial Documents

#### Story 8: Document-Centered Posting

As a student, I want to create accounting entries from common commercial documents so that the simulation starts from the source document, not only from abstract journal lines.

Acceptance criteria:
- Source flows for at least:
  - invoice
  - receipt
  - promissory note
  - cheque
  - credit note
  - debit note
- Generated journal entries remain immutable.
- Document flows can still be explained and overridden by teachers for didactic purposes.

### Epic: Societies and Profit Distribution

#### Story 9: Profit/Loss Distribution

As a teacher, I want to register distribution of results so that SIC can cover the post-closing treatment proposed by the book.

Acceptance criteria:
- Distribution of profit:
  - to capital
  - to reserve
  - to partners
- Absorption of loss:
  - through reserves
  - through partners
  - through capital
- Compatible with closed-exercise snapshots and reopening logic.

#### Story 10: Society Support

As a teacher, I want society-aware companies so that the system can simulate partner-based accounting scenarios.

Acceptance criteria:
- Company can optionally define a society type.
- Support partner-specific accounts where needed.
- Preserve current single-owner flows for simpler scenarios.
- Keeps current student/demo company flows working unchanged when society features are unused.

### Epic: Pedagogical Layer

#### Story 11: Patrimonial Variation Classification

As a student, I want each practice operation to be classifiable as permutative or modificative so that the platform reinforces the conceptual model from SIC 1.

Acceptance criteria:
- Optional classification metadata per operation/exercise.
- UI/API can explain the expected variation type.
- Supports:
  - permutative
  - modificative positive
  - modificative negative
- Does not force this metadata on every accounting entry when not needed.

#### Story 12: Guided Learning Scenarios

As a teacher, I want guided accounting scenarios by level so that the same backend can support different years of secondary school.

Acceptance criteria:
- Beginner, intermediate and advanced demo/scenario profiles.
- Optional teaching hints.
- Can be tied to demo companies or structured exercises.
- Supports the existing demo system instead of replacing it.

## Enablers and Dependencies

These items are not always user-facing, but they reduce implementation risk.

### Enabler A: Reporting Contracts

Needed by:

- Standalone Balance Sheet
- Standalone Income Statement
- Inventory and Balances Book

Work:

- standardize report metadata for:
  - requested range
  - effective exercise range
  - visible range
- keep export contracts stable
- document report invariants clearly

### Enabler B: Adjustment Abstractions

Needed by:

- Advanced Closing Adjustments
- Debtor Cleansing
- Profit/Loss Distribution

Work:

- define adjustment draft types
- define confirmation flow versus preview flow
- preserve immutable final posting

### Enabler C: Document Source Model

Needed by:

- Document-Centered Posting
- IVA Books
- IVA Liquidation

Work:

- decide whether documents are:
  - lightweight source descriptors
  - or first-class persisted entities
- define minimal numbering/reference conventions
- define tax metadata needed for IVA flows

## Suggested Release Roadmap

This is a pragmatic sequencing proposal, not a hard commitment.

### Release Band 1: Reporting Completion

Focus:

- Standalone Balance Sheet
- Standalone Income Statement
- Inventory and Balances Book

Why first:

- highest user value
- lowest conceptual disruption
- strongest improvement to SIC 1 compliance
- builds directly on what the backend already does

### Release Band 2: Closing and Adjustment Depth

Focus:

- Advanced Closing Adjustments
- Debtor Cleansing
- better pre-close visibility

Why second:

- deepens the accounting realism
- reuses the current closing workflow and snapshots

### Release Band 3: IVA

Focus:

- IVA Purchases Book
- IVA Sales Book
- IVA Monthly Liquidation

Why third:

- major SIC 1 coverage gain
- pedagogically very valuable
- benefits from prior reporting maturity

### Release Band 4: Commercial Documents

Focus:

- invoice
- receipt
- cheque
- promissory note
- debit/credit note

Why fourth:

- strong didactic payoff
- easier to build once reporting and IVA semantics are stable

### Release Band 5: Societies and Distribution

Focus:

- society support
- profit/loss distribution

Why fifth:

- important for full coverage
- less central than the prior bands for early classroom value

### Release Band 6: Pedagogical Overlays

Focus:

- patrimonial variation classification
- guided scenarios
- hints and level-based teaching flows

Why sixth:

- highest teaching value once the accounting substrate is mature
- should sit on top of a stable core, not substitute for it

## Longer-Term Opportunities

- Formal `Exercise/FiscalPeriod` domain model.
- Worksheet / 12-column pre-balance as first-class report.
- Statement of changes in equity.
- Funds flow / origin and application of funds.
- Teacher assessment tools and correction workflows.
- More granular auxiliaries:
  - cash
  - banks
  - customers
  - suppliers
- scenario authoring tools for teachers
- course-level progress analytics
- export-friendly legal-style printable books
- stronger audit timeline for demo and student companies

## Out of Scope For the Immediate Next Phase

These may be useful later, but should not distract from the next product step:

- ERP-style inventory management
- payroll subsystem with HR depth
- full tax engine beyond SIC 1 educational needs
- multi-currency accounting
- banking reconciliation as a separate product area
- complex enterprise procurement workflows

## Readiness Checklist For New Stories

A story is ready to enter a sprint when:

- its accounting rule is clear
- its didactic objective is clear
- its reporting impact is known
- its interaction with logical exercises is defined
- its impact on closing is defined when relevant
- its API contract is sketched
- its migration impact is understood
- its demo/test coverage strategy is identified

## Success Metrics

The backlog should improve the product in measurable ways.

Examples:

- more SIC 1 units covered end-to-end
- more teacher-usable classroom scenarios
- fewer frontend workarounds for accounting interpretation
- broader demo richness without breaking accounting correctness
- higher reuse of the same core rules across reports, closing and educational flows

## Prioritization Guidance

Recommended order:

1. Standalone balance sheet and income statement
2. Inventory and balances book
3. IVA books and monthly liquidation
4. Advanced adjustments
5. Profit/loss distribution
6. Commercial document flows
7. Society support
8. Pedagogical overlays

## Maintainer Note

This backlog is intentionally product-oriented.

Implementation should continue to respect the architecture already established in the repository:

- accounting truth comes from journal entries
- reports derive from accounting truth
- closing remains transactional and auditable
- demos and teaching layers should reuse the same accounting engine
