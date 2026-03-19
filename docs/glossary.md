# Glossary

This glossary mixes technical and accounting language used in the project.

It is intentionally short and practical.

## Accounting Terms

### Asset

An account category representing resources controlled by the company.

In SIC terms, asset accounts normally carry debit balances or are settled.

### Liability

An account category representing obligations owed to third parties.

In SIC terms, liability accounts normally carry credit balances or are settled.

### Equity

The residual interest after liabilities are deducted from assets.

In the chart, this corresponds to patrimonial/equity accounts.

### Positive Result

An income or gain account that increases results.

These accounts normally carry credit balances.

### Negative Result

An expense or loss account that decreases results.

These accounts normally carry debit balances.

### Journal Entry

An accounting posting made of debit and credit lines.

In the book terminology, this corresponds to an `asiento`.

### Simple Entry

An entry with one debit account and one credit account.

### Compound Entry

An entry with more than one participating account on the debit side, credit side, or both.

### Double-Entry Bookkeeping

The method by which every accounting operation is recorded through balanced debit and credit effects.

This is one of the strongest invariants of the backend.

### Opening Entry

The first formal accounting entry that initializes a company's books for a new activity or first exercise.

### Closing

The end-of-exercise process that cancels result accounts, closes patrimonial balances and prepares the next accounting cycle.

### Reopening

The entry that opens patrimonial balances again at the beginning of the next exercise.

### Trial Balance

The report that lists accounts and balances to verify debit/credit equality and inspect the state of the ledger.

In Spanish accounting teaching, this maps to `balance de comprobacion`.

### Ledger

The report that groups movements and balances by account.

In Spanish accounting teaching, this maps to `libro mayor`.

### Journal Book

The chronological report of journal entries.

In Spanish accounting teaching, this maps to `libro diario`.

### Patrimonial Variation

A conceptual classification of how an operation affects the patrimony of the company.

Common teaching categories:

- permutative
- positive modificative
- negative modificative

### IVA

Value-added tax accounting used in Argentine bookkeeping.

The current backend supports IVA accounts in the chart and manual postings, but not yet the full IVA subsystem proposed by SIC 1.

### Cash Arqueo

Cash count adjustment performed at closing to compare accounting balance with actual cash on hand.

### Inventory Difference

A year-end difference between accounting inventory and physically observed inventory.

## Project Terms

### Rubro

Top-level account grouping in the chart.

### Colectiva

Intermediate shared account group under a rubro.

### Movement Account

A company-level operational account used for actual posting.

### Logical Exercise

The project's inferred fiscal period model.

It is not yet a first-class persisted `Exercise` entity.

### Closing Snapshot

An immutable record of a confirmed close, including formal balance sheet and income statement outputs.

### Demo Company

A read-only company imported for teaching, onboarding or smoke validation.

### Publication

The global visibility status of a demo company.

Published and unpublished are separate concepts from read-only and course-level visibility.
