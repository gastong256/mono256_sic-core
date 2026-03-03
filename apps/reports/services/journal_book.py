"""
Libro Diario (Journal Book) report service.

Chronological list of all journal entries within a date range,
each with its full set of lines and per-entry totals.
"""

import datetime
from decimal import Decimal

from apps.companies.models import Company
from apps.journal.models import JournalEntry, JournalEntryLine

_ZERO = Decimal("0")


def get_journal_book(
    *,
    company: Company,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
) -> dict:
    """
    Build the Libro Diario report for the given company and date range.

    DB queries: 3 (entries, prefetch lines, prefetch accounts) —
    bounded regardless of the number of entries.

    Returns an empty entries list if no data matches, not an error.
    """
    actual_date_to = date_to or datetime.date.today()

    qs = (
        JournalEntry.objects.filter(company=company)
        .order_by("date", "entry_number")
        .prefetch_related("lines__account")
    )
    if date_from:
        qs = qs.filter(date__gte=date_from)
    qs = qs.filter(date__lte=actual_date_to)

    entries = list(qs)

    if date_from:
        actual_date_from = date_from
    elif entries:
        actual_date_from = entries[0].date
    else:
        actual_date_from = actual_date_to

    entries_data = []
    grand_debit = _ZERO
    grand_credit = _ZERO

    for entry in entries:
        lines_data = []
        entry_debit = _ZERO
        entry_credit = _ZERO

        for line in entry.lines.all():
            if line.type == JournalEntryLine.LineType.DEBIT:
                lines_data.append({
                    "account_code": line.account.full_code,
                    "account_name": line.account.name,
                    "debit": f"{line.amount:.2f}",
                    "credit": None,
                })
                entry_debit += line.amount
            else:
                lines_data.append({
                    "account_code": line.account.full_code,
                    "account_name": line.account.name,
                    "debit": None,
                    "credit": f"{line.amount:.2f}",
                })
                entry_credit += line.amount

        grand_debit += entry_debit
        grand_credit += entry_credit

        entries_data.append({
            "entry_number": entry.entry_number,
            "date": str(entry.date),
            "description": entry.description,
            "source_type": entry.source_type,
            "source_ref": entry.source_ref,
            "lines": lines_data,
            "total_debit": f"{entry_debit:.2f}",
            "total_credit": f"{entry_credit:.2f}",
        })

    return {
        "company": company.name,
        "date_from": str(actual_date_from),
        "date_to": str(actual_date_to),
        "entries": entries_data,
        "totals": {
            "total_debit": f"{grand_debit:.2f}",
            "total_credit": f"{grand_credit:.2f}",
        },
    }
