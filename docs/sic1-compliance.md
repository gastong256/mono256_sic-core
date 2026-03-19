# SIC 1 Compliance Assessment

This document evaluates the current backend implementation against the scope and teaching line proposed in:

`SIC - Sistemas de Informacion Contable`

Angrisani Editores - Ed. 2019

## Current Score

Current compliance score: `7/10`

## Scope Covered Well

The backend already covers the strongest operational accounting core of SIC 1:

- opening entry / initial inventory
- double-entry bookkeeping
- immutable journal entries
- chart of accounts base structure
- journal book
- ledger
- trial balance
- simplified year-end closing
- patrimonial closing
- reopening
- inferred logical fiscal exercises
- immutable closing snapshots

Relevant implementation references:
- [apps/companies/opening.py](/home/gastong256/projects/mono256_sic-core/apps/companies/opening.py)
- [apps/journal/models.py](/home/gastong256/projects/mono256_sic-core/apps/journal/models.py)
- [apps/journal/services.py](/home/gastong256/projects/mono256_sic-core/apps/journal/services.py)
- [apps/reports/services/journal_book.py](/home/gastong256/projects/mono256_sic-core/apps/reports/services/journal_book.py)
- [apps/reports/services/ledger.py](/home/gastong256/projects/mono256_sic-core/apps/reports/services/ledger.py)
- [apps/reports/services/trial_balance.py](/home/gastong256/projects/mono256_sic-core/apps/reports/services/trial_balance.py)
- [apps/closing/services.py](/home/gastong256/projects/mono256_sic-core/apps/closing/services.py)
- [apps/closing/selectors.py](/home/gastong256/projects/mono256_sic-core/apps/closing/selectors.py)

## Scope Covered Partially

### States and year-end reporting

The backend already builds:

- `balance_sheet`
- `income_statement`

but only inside:

- closing preview
- immutable closing snapshots

It does not yet expose them as standalone dynamic reports for any arbitrary date.

### Fiscal exercise

The system supports logical exercises inferred from:

- `OPENING`
- `REOPENING`
- `PATRIMONIAL_CLOSING`

This is strong enough operationally, but it is not yet a formal persisted `Exercise/FiscalPeriod` model.

### IVA

The base chart includes:

- `IVA Crédito Fiscal`
- `IVA Débito Fiscal`
- `IVA Saldo a Pagar`

and entries can represent IVA manually, but there is still no dedicated IVA subsystem with:

- IVA Purchases Book
- IVA Sales Book
- monthly IVA liquidation workflow

### Adjustments

The current closing supports:

- cash arqueo
- inventory differences

but not yet the broader set of adjustments described by SIC 1.

## Scope Not Yet Covered

The following topics from SIC 1 are not yet fully implemented as first-class features:

- commercial documents as a real subdomain
  - purchase order
  - remito
  - invoice
  - ticket
  - credit note
  - debit note
  - receipt
  - promissory note
  - cheque
  - deposit slip
- inventory and balances book
- worksheet / 12-column pre-balance
- standalone balance sheet
- standalone income statement
- statement of changes in equity
- funds flow / origin and application of funds
- profit/loss distribution
- societies and partner-specific flows
- explicit didactic classification of patrimonial variations
- advanced adjustments:
  - debtor cleansing
  - protested documents / legal collection
  - accruals
  - prepaid expenses
  - accrued income
  - unpaid expenses
  - amortization
  - omitted bank charges

## Why the Score Is 7/10

The project is already strong enough to support a realistic educational accounting engine.

However, SIC 1 is broader than core posting and closing. The book also expects:

- document flow as accounting sources
- tax/IVA treatment
- balance preparation workflow
- formal statements
- profit distribution
- society-related accounting concepts
- explicit educational framing for patrimonial variations

Because of that, the project is beyond “basic prototype”, but not yet at full SIC 1 coverage.

## What Is Missing For 10/10

1. Dynamic standalone reports for:
   - balance sheet / estado de situación patrimonial
   - income statement / estado de resultados
2. Inventory and balances book.
3. IVA subsystem:
   - IVA purchases book
   - IVA sales book
   - monthly IVA liquidation
4. 12-column worksheet / pre-balance.
5. Advanced balance adjustments.
6. Profit and loss distribution.
7. Society domain support.
8. Didactic layer for patrimonial variation classification.
9. Optional formal `Exercise/FiscalPeriod` entity for maximum accounting rigor.

## Recommended Product Direction

The best next step is not to broaden randomly, but to continue in layers:

1. complete the accounting reporting layer
2. add IVA and adjustments
3. add document-driven flows
4. add society/distribution logic
5. add didactic workflows on top of the core

## Summary

Current state:

- core accounting engine: strong
- closing workflow: strong
- educational usefulness: high
- full SIC 1 coverage: incomplete

Final score: `7/10`
