import datetime
from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping, Sequence

from django.db import IntegrityError, transaction
from moneyed import Money
from rest_framework.exceptions import ValidationError

from hordak.models import Account, Leg
from hordak.models import Transaction as HordakTransaction

from config.exceptions import ConflictError
from apps.companies.opening import assert_company_accounting_ready, company_has_opening_entry
from apps.companies.models import Company, CompanyAccount
from apps.companies.services import assert_company_writable
from apps.journal.models import JournalEntry, JournalEntryLine
from apps.reports.cache import bump_report_cache_version

NON_REVERSIBLE_SOURCE_TYPES = frozenset(
    {
        JournalEntry.SourceType.OPENING,
        JournalEntry.SourceType.ADJUSTMENT,
        JournalEntry.SourceType.RESULT_CLOSING,
        JournalEntry.SourceType.PATRIMONIAL_CLOSING,
        JournalEntry.SourceType.REOPENING,
    }
)


@dataclass(frozen=True)
class JournalLineInput:
    account_id: int
    type: str
    amount: Decimal


def _assert_books_open(*, company: Company, date: datetime.date) -> None:
    """Hard stop for closed periods; entries are immutable after closing."""
    if company.books_closed_until and date <= company.books_closed_until:
        raise ConflictError(
            f"Books are closed until {company.books_closed_until}. "
            f"Use a date after {company.books_closed_until}."
        )


def _normalize_lines(*, lines: Sequence[Mapping[str, object]]) -> list[JournalLineInput]:
    return [
        JournalLineInput(
            account_id=int(line["account_id"]),
            type=str(line["type"]),
            amount=Decimal(str(line["amount"])),
        )
        for line in lines
    ]


def _validate_lines(lines: Sequence[JournalLineInput], company: Company) -> dict[int, Account]:
    """
    Validate Angrisani asiento rules before any write:
    - at least one debit and one credit
    - balanced totals
    - positive amounts
    - only company movement accounts (MPTT level=2 leaf)
    """
    if not lines:
        raise ValidationError("El asiento debe tener al menos una línea deudora y una acreedora.")

    account_ids = {line.account_id for line in lines}
    accounts = {account.pk: account for account in Account.objects.filter(pk__in=account_ids)}
    missing = account_ids - set(accounts.keys())
    if missing:
        missing_id = min(missing)
        raise ValidationError(f"La cuenta con id {missing_id} no existe.")

    company_account_ids = set(
        CompanyAccount.objects.filter(
            company=company,
            account_id__in=account_ids,
        ).values_list("account_id", flat=True)
    )

    debit_total = Decimal("0")
    credit_total = Decimal("0")
    has_debit = False
    has_credit = False

    for line in lines:
        amount = line.amount
        line_type = line.type
        account_id = line.account_id

        if amount <= 0:
            raise ValidationError("El importe de cada línea debe ser mayor a cero.")

        account = accounts[account_id]

        if account.level != 2:
            raise ValidationError(
                f"La cuenta {account.full_code} no es una cuenta de movimiento (nivel 3)."
            )

        if not account.is_leaf_node():
            raise ValidationError(
                f"La cuenta {account.full_code} no es una cuenta de movimiento (tiene subcuentas)."
            )

        if account_id not in company_account_ids:
            raise ValidationError(f"La cuenta {account.full_code} no pertenece a esta empresa.")

        if line_type == JournalEntryLine.LineType.DEBIT:
            debit_total += amount
            has_debit = True
        else:
            credit_total += amount
            has_credit = True

    if not has_debit or not has_credit:
        raise ValidationError("El asiento debe tener al menos una línea deudora y una acreedora.")

    if debit_total != credit_total:
        raise ValidationError("El total de débitos debe ser igual al total de créditos.")
    return accounts


def _next_entry_number(company: Company) -> int:
    """Sequential per-company numbering with row locks to avoid races."""
    Company.objects.select_for_update().filter(pk=company.pk).exists()

    last = (
        JournalEntry.objects.select_for_update()
        .filter(company=company)
        .order_by("-entry_number")
        .first()
    )
    return (last.entry_number + 1) if last else 1


@transaction.atomic
def create_journal_entry(
    *,
    company: Company,
    created_by,
    date: datetime.date,
    description: str,
    source_type: str = JournalEntry.SourceType.MANUAL,
    source_ref: str = "",
    lines: list[dict],
) -> JournalEntry:
    """Create and post an immutable asiento (Hordak transaction + legs + mirror lines)."""
    assert_company_writable(company=company)
    if source_type == JournalEntry.SourceType.OPENING:
        if company_has_opening_entry(company=company):
            raise ConflictError("This company already has an opening entry.")
        if company.journal_entries.exists():
            raise ConflictError("Opening entry must be the first accounting entry of the company.")
    else:
        assert_company_accounting_ready(company=company)
    _assert_books_open(company=company, date=date)
    normalized_lines = _normalize_lines(lines=lines)
    accounts = _validate_lines(normalized_lines, company)
    next_number = _next_entry_number(company)

    hordak_tx = HordakTransaction.objects.create(
        date=date,
        description=description,
    )

    legs_to_create: list[Leg] = []
    for line in normalized_lines:
        account = accounts[line.account_id]
        currency = account.currencies[0]
        money = Money(line.amount, currency)

        if line.type == JournalEntryLine.LineType.DEBIT:
            legs_to_create.append(Leg(transaction=hordak_tx, account=account, debit=money))
        else:
            legs_to_create.append(Leg(transaction=hordak_tx, account=account, credit=money))
    Leg.objects.bulk_create(legs_to_create)

    try:
        entry = JournalEntry.objects.create(
            transaction=hordak_tx,
            company=company,
            entry_number=next_number,
            date=date,
            description=description,
            source_type=source_type,
            source_ref=source_ref,
            created_by=created_by,
        )
    except IntegrityError:
        raise ConflictError("Another entry was created concurrently. Please retry.")

    JournalEntryLine.objects.bulk_create(
        [
            JournalEntryLine(
                journal_entry=entry,
                account_id=line.account_id,
                type=line.type,
                amount=line.amount,
            )
            for line in normalized_lines
        ]
    )

    bump_report_cache_version(company_id=company.id)

    return entry


@transaction.atomic
def reverse_journal_entry(
    *,
    company: Company,
    original_entry: JournalEntry,
    created_by,
    date: datetime.date | None = None,
    description: str = "",
) -> JournalEntry:
    """Create contra-entry by swapping debit/credit on every original line."""
    assert_company_writable(company=company)
    assert_company_accounting_ready(company=company)
    if original_entry.company_id != company.pk:
        raise ValidationError("Asiento contable no encontrado.")
    if original_entry.source_type in NON_REVERSIBLE_SOURCE_TYPES:
        raise ConflictError("This entry type cannot be reversed.")

    if JournalEntry.objects.filter(reversal_of=original_entry).exists():
        raise ConflictError("This entry has already been reversed.")

    reversal_date = date or datetime.date.today()
    _assert_books_open(company=company, date=reversal_date)

    original_lines = list(original_entry.lines.select_related("account").all())
    if not original_lines:
        raise ValidationError("Cannot reverse an entry with no lines.")

    reversed_lines: list[JournalLineInput] = []
    account_map = {line.account_id: line.account for line in original_lines}
    for line in original_lines:
        reversed_type = (
            JournalEntryLine.LineType.CREDIT
            if line.type == JournalEntryLine.LineType.DEBIT
            else JournalEntryLine.LineType.DEBIT
        )
        reversed_lines.append(
            JournalLineInput(
                account_id=line.account_id,
                type=reversed_type,
                amount=line.amount,
            )
        )

    reversal_description = (
        description.strip()
        or f"Reversión de asiento #{original_entry.entry_number}: {original_entry.description}"
    )
    reversal_ref = f"REV-{original_entry.entry_number}"
    next_number = _next_entry_number(company)

    hordak_tx = HordakTransaction.objects.create(
        date=reversal_date,
        description=reversal_description,
    )

    legs_to_create: list[Leg] = []
    for line in reversed_lines:
        account = account_map[line.account_id]
        currency = account.currencies[0]
        money = Money(line.amount, currency)
        if line.type == JournalEntryLine.LineType.DEBIT:
            legs_to_create.append(Leg(transaction=hordak_tx, account=account, debit=money))
        else:
            legs_to_create.append(Leg(transaction=hordak_tx, account=account, credit=money))
    Leg.objects.bulk_create(legs_to_create)

    try:
        reversal_entry = JournalEntry.objects.create(
            transaction=hordak_tx,
            company=company,
            entry_number=next_number,
            date=reversal_date,
            description=reversal_description,
            source_type=JournalEntry.SourceType.OTHER,
            source_ref=reversal_ref,
            created_by=created_by,
            reversal_of=original_entry,
        )
    except IntegrityError:
        raise ConflictError("Another entry was created concurrently. Please retry.")

    JournalEntryLine.objects.bulk_create(
        [
            JournalEntryLine(
                journal_entry=reversal_entry,
                account_id=line.account_id,
                type=line.type,
                amount=line.amount,
            )
            for line in reversed_lines
        ]
    )

    bump_report_cache_version(company_id=company.id)

    return reversal_entry
