import datetime
from decimal import Decimal

from apps.closing.selectors import resolve_report_exercise_context
from apps.companies.models import Company
from apps.journal.models import JournalEntry, JournalEntryLine
from apps.reports import cache as report_cache
from apps.reports.exercise_context import (
    attach_report_exercise_metadata,
    build_report_exercise_cache_parts,
)

_ZERO = Decimal("0")


def get_journal_book(
    *,
    company: Company,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
) -> dict:
    """Libro Diario: chronological entries with full lines and per-entry totals."""
    context = resolve_report_exercise_context(
        company=company,
        date_from=date_from,
        date_to=date_to,
    )
    cache_extra_parts = build_report_exercise_cache_parts(context=context)
    actual_date_to = context.visible_to
    cached = report_cache.get_cached_report(
        report_name="journal_book",
        company_id=company.id,
        date_from=context.visible_from,
        date_to=actual_date_to,
        extra_parts=cache_extra_parts,
    )
    if cached is not None:
        return attach_report_exercise_metadata(report=cached, context=context)

    qs = (
        JournalEntry.objects.filter(company=company)
        .order_by("date", "entry_number")
        .prefetch_related("lines__account")
    )
    if context.visible_from:
        qs = qs.filter(date__gte=context.visible_from)
    qs = qs.filter(date__lte=actual_date_to)

    entries = list(qs)

    if context.visible_from:
        actual_date_from = context.visible_from
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
                lines_data.append(
                    {
                        "account_code": line.account.full_code,
                        "account_name": line.account.name,
                        "debit": f"{line.amount:.2f}",
                        "credit": None,
                    }
                )
                entry_debit += line.amount
            else:
                lines_data.append(
                    {
                        "account_code": line.account.full_code,
                        "account_name": line.account.name,
                        "debit": None,
                        "credit": f"{line.amount:.2f}",
                    }
                )
                entry_credit += line.amount

        grand_debit += entry_debit
        grand_credit += entry_credit

        entries_data.append(
            {
                "entry_number": entry.entry_number,
                "date": str(entry.date),
                "description": entry.description,
                "source_type": entry.source_type,
                "source_ref": entry.source_ref,
                "lines": lines_data,
                "total_debit": f"{entry_debit:.2f}",
                "total_credit": f"{entry_credit:.2f}",
            }
        )

    report = {
        "company_id": company.id,
        "company": company.name,
        "date_from": str(actual_date_from),
        "date_to": str(actual_date_to),
        "entries": entries_data,
        "grand_total_debit": f"{grand_debit:.2f}",
        "grand_total_credit": f"{grand_credit:.2f}",
        "totals": {
            "total_debit": f"{grand_debit:.2f}",
            "total_credit": f"{grand_credit:.2f}",
        },
    }
    report_cache.set_cached_report(
        report_name="journal_book",
        company_id=company.id,
        date_from=context.visible_from,
        date_to=actual_date_to,
        extra_parts=cache_extra_parts,
        value=report,
        is_demo=company.is_demo,
    )
    return attach_report_exercise_metadata(report=report, context=context)
