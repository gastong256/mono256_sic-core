import datetime
from collections import defaultdict
from decimal import Decimal

from django.db.models import Q, Sum

from hordak.models import Account

from apps.companies.models import Company
from apps.journal.models import JournalEntryLine

_ZERO = Decimal("0")

_DEBIT_NORMAL = frozenset({"AS", "EX"})
_CREDIT_NORMAL = frozenset({"LI", "EQ", "IN"})


def _balance_delta(account_type: str, debit: Decimal, credit: Decimal) -> Decimal:
    """Apply normal-balance convention (debit-normal vs credit-normal accounts)."""
    if account_type in _DEBIT_NORMAL:
        return debit - credit
    return credit - debit


def get_ledger(
    *,
    company: Company,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
    account_id: int | None = None,
) -> dict:
    """Libro Mayor (Mayor Americano): opening, movements, and closing balance by account."""
    from rest_framework.exceptions import ValidationError

    actual_date_to = date_to or datetime.date.today()

    account_qs = Account.objects.filter(company_account__company=company).order_by("full_code")

    if account_id is not None:
        account_qs = account_qs.filter(pk=account_id)
        if not account_qs.exists():
            raise ValidationError({"account_id": "ID de cuenta inválido."})

    accounts = list(account_qs)
    account_ids = [a.pk for a in accounts]
    account_map = {a.pk: a for a in accounts}

    if not accounts:
        return {
            "company_id": company.id,
            "company": company.name,
            "date_from": str(date_from or actual_date_to),
            "date_to": str(actual_date_to),
            "account_id": account_id,
            "cards": [],
            "accounts": [],
        }

    opening_balances: dict[int, Decimal] = {pk: _ZERO for pk in account_ids}
    if date_from:
        opening_rows = (
            JournalEntryLine.objects.filter(
                account_id__in=account_ids,
                journal_entry__company=company,
                journal_entry__date__lt=date_from,
            )
            .values("account_id")
            .annotate(
                debit_sum=Sum("amount", filter=Q(type=JournalEntryLine.LineType.DEBIT)),
                credit_sum=Sum("amount", filter=Q(type=JournalEntryLine.LineType.CREDIT)),
            )
        )
        for row in opening_rows:
            debit = row["debit_sum"] or _ZERO
            credit = row["credit_sum"] or _ZERO
            acct = account_map[row["account_id"]]
            opening_balances[acct.pk] = _balance_delta(acct.type, debit, credit)

    movement_filter = Q(
        account_id__in=account_ids,
        journal_entry__company=company,
        journal_entry__date__lte=actual_date_to,
    )
    if date_from:
        movement_filter &= Q(journal_entry__date__gte=date_from)

    movements_qs = (
        JournalEntryLine.objects.filter(movement_filter)
        .select_related("journal_entry")
        .order_by("account_id", "journal_entry__date", "journal_entry__entry_number")
    )

    movements_by_account: dict[int, list] = defaultdict(list)
    for line in movements_qs:
        movements_by_account[line.account_id].append(line)

    if date_from:
        actual_date_from = date_from
    else:
        all_dates = [
            line.journal_entry.date for lines in movements_by_account.values() for line in lines
        ]
        actual_date_from = min(all_dates) if all_dates else actual_date_to

    accounts_data = []
    for account in accounts:
        opening = opening_balances[account.pk]
        running = opening
        period_debit = _ZERO
        period_credit = _ZERO
        movements_data = []

        for line in movements_by_account.get(account.pk, []):
            if line.type == JournalEntryLine.LineType.DEBIT:
                debit_str: str | None = f"{line.amount:.2f}"
                credit_str: str | None = None
                period_debit += line.amount
            else:
                debit_str = None
                credit_str = f"{line.amount:.2f}"
                period_credit += line.amount

            running += _balance_delta(
                account.type,
                line.amount if debit_str else _ZERO,
                line.amount if credit_str else _ZERO,
            )
            movements_data.append(
                {
                    "date": str(line.journal_entry.date),
                    "entry_number": line.journal_entry.entry_number,
                    "description": line.journal_entry.description,
                    "source_ref": line.journal_entry.source_ref,
                    "debit": debit_str,
                    "credit": credit_str,
                    "balance": f"{running:.2f}",
                }
            )

        closing = opening + _balance_delta(account.type, period_debit, period_credit)

        accounts_data.append(
            {
                "account_code": account.full_code,
                "account_name": account.name,
                "account_type": account.type,
                "normal_balance": "DEBIT" if account.type in _DEBIT_NORMAL else "CREDIT",
                "opening_balance": f"{opening:.2f}",
                "movements": movements_data,
                "period_totals": {
                    "total_debit": f"{period_debit:.2f}",
                    "total_credit": f"{period_credit:.2f}",
                },
                "closing_balance": f"{closing:.2f}",
            }
        )

    return {
        "company_id": company.id,
        "company": company.name,
        "date_from": str(actual_date_from),
        "date_to": str(actual_date_to),
        "account_id": account_id,
        "cards": accounts_data,
        "accounts": accounts_data,
    }
