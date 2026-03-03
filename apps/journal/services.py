import datetime
from decimal import Decimal

from django.db import transaction
from moneyed import Money
from rest_framework.exceptions import ValidationError

from hordak.models import Account, Leg
from hordak.models import Transaction as HordakTransaction

from apps.companies.models import Company, CompanyAccount
from apps.journal.models import JournalEntry, JournalEntryLine


def _validate_lines(lines: list[dict], company: Company) -> None:
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

        try:
            account = Account.objects.get(pk=account_id)
        except Account.DoesNotExist:
            raise ValidationError(
                f"La cuenta con id {account_id} no existe."
            )

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
        if not CompanyAccount.objects.filter(account=account, company=company).exists():
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


def _next_entry_number(company: Company) -> int:
    """
    Return the next sequential entry number for the given company.

    Uses select_for_update to avoid race conditions under concurrent requests.
    Must be called inside an atomic block.
    """
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
    _validate_lines(lines, company)
    next_number = _next_entry_number(company)

    hordak_tx = HordakTransaction.objects.create(
        date=date,
        description=description,
    )

    for line in lines:
        account = Account.objects.get(pk=line["account_id"])
        currency = account.currencies[0]
        money = Money(line["amount"], currency)

        if line["type"] == JournalEntryLine.LineType.DEBIT:
            Leg.objects.create(transaction=hordak_tx, account=account, debit=money)
        else:
            Leg.objects.create(transaction=hordak_tx, account=account, credit=money)

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
