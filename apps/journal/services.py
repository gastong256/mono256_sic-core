import datetime
from decimal import Decimal

from django.db import IntegrityError, transaction
from moneyed import Money
from rest_framework.exceptions import ValidationError

from hordak.models import Account, Leg
from hordak.models import Transaction as HordakTransaction

from config.exceptions import ConflictError
from apps.companies.models import Company, CompanyAccount
from apps.journal.models import JournalEntry, JournalEntryLine


def _assert_books_open(*, company: Company, date: datetime.date) -> None:
    """Ensure the requested accounting date is not in a closed period."""
    if company.books_closed_until and date <= company.books_closed_until:
        raise ConflictError(
            f"Books are closed until {company.books_closed_until}. "
            f"Use a date after {company.books_closed_until}."
        )


def _validate_lines(lines: list[dict], company: Company) -> dict[int, Account]:
    """
    Enforce all business rules on the entry lines before any DB write.

    Rules checked:
      1. At least one DEBIT and one CREDIT line.
      2. Sum of DEBIT amounts equals sum of CREDIT amounts.
      3. Every amount is strictly positive.
      4. Every account is level-2 (MPTT), is a leaf node,
         and belongs to the given company via CompanyAccount.
    """
    if not lines:
        raise ValidationError(
            "El asiento debe tener al menos una línea deudora y una acreedora."
        )

    account_ids = {line["account_id"] for line in lines}
    accounts = {
        account.pk: account
        for account in Account.objects.filter(pk__in=account_ids)
    }
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
        amount: Decimal = line["amount"]
        line_type: str = line["type"]
        account_id: int = line["account_id"]

        # Rule 5: positive amounts
        if amount <= 0:
            raise ValidationError(
                "El importe de cada línea debe ser mayor a cero."
            )

        account = accounts[account_id]

        # Rule 3: account must be MPTT level=2 (depth-3)
        if account.level != 2:
            raise ValidationError(
                f"La cuenta {account.full_code} no es una cuenta de movimiento (nivel 3)."
            )

        # Rule 4: account must be a leaf node
        if not account.is_leaf_node():
            raise ValidationError(
                f"La cuenta {account.full_code} no es una cuenta de movimiento (tiene subcuentas)."
            )

        # Rule 3: account must belong to this company
        if account_id not in company_account_ids:
            raise ValidationError(
                f"La cuenta {account.full_code} no pertenece a esta empresa."
            )

        if line_type == JournalEntryLine.LineType.DEBIT:
            debit_total += amount
            has_debit = True
        else:
            credit_total += amount
            has_credit = True

    # Rule 2: minimum lines (at least one debit and one credit)
    if not has_debit or not has_credit:
        raise ValidationError(
            "El asiento debe tener al menos una línea deudora y una acreedora."
        )

    # Rule 1: balanced entry
    if debit_total != credit_total:
        raise ValidationError(
            "El total de débitos debe ser igual al total de créditos."
        )
    return accounts


def _next_entry_number(company: Company) -> int:
    """
    Return the next sequential entry number for the given company.

    Uses select_for_update to avoid race conditions under concurrent requests.
    Must be called inside an atomic block.
    """
    # Lock the company row first so first-entry races are also serialized.
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
    """
    Validate, post, and persist a new journal entry for the given company.

    All business rules are checked before any write.
    Creates a hordak Transaction + Legs for double-entry accounting,
    then creates the JournalEntry and its JournalEntryLines atomically.

    Raises ValidationError for any business rule violation.
    """
    _assert_books_open(company=company, date=date)
    accounts = _validate_lines(lines, company)
    next_number = _next_entry_number(company)

    hordak_tx = HordakTransaction.objects.create(
        date=date,
        description=description,
    )

    legs_to_create: list[Leg] = []
    for line in lines:
        account = accounts[line["account_id"]]
        currency = account.currencies[0]
        money = Money(line["amount"], currency)

        if line["type"] == JournalEntryLine.LineType.DEBIT:
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

    JournalEntryLine.objects.bulk_create([
        JournalEntryLine(
            journal_entry=entry,
            account_id=line["account_id"],
            type=line["type"],
            amount=line["amount"],
        )
        for line in lines
    ])

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
    """Create a contra-entry that fully reverses the original journal entry."""
    if original_entry.company_id != company.pk:
        raise ValidationError("Asiento contable no encontrado.")

    if JournalEntry.objects.filter(reversal_of=original_entry).exists():
        raise ConflictError("This entry has already been reversed.")

    reversal_date = date or datetime.date.today()
    _assert_books_open(company=company, date=reversal_date)

    original_lines = list(
        original_entry.lines.select_related("account").all()
    )
    if not original_lines:
        raise ValidationError("Cannot reverse an entry with no lines.")

    reversed_lines: list[dict] = []
    account_map = {line.account_id: line.account for line in original_lines}
    for line in original_lines:
        reversed_type = (
            JournalEntryLine.LineType.CREDIT
            if line.type == JournalEntryLine.LineType.DEBIT
            else JournalEntryLine.LineType.DEBIT
        )
        reversed_lines.append({
            "account_id": line.account_id,
            "type": reversed_type,
            "amount": line.amount,
        })

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
        account = account_map[line["account_id"]]
        currency = account.currencies[0]
        money = Money(line["amount"], currency)
        if line["type"] == JournalEntryLine.LineType.DEBIT:
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

    JournalEntryLine.objects.bulk_create([
        JournalEntryLine(
            journal_entry=reversal_entry,
            account_id=line["account_id"],
            type=line["type"],
            amount=line["amount"],
        )
        for line in reversed_lines
    ])

    return reversal_entry
