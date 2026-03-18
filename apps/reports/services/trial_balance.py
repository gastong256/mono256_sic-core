import datetime
from decimal import Decimal

from django.db.models import Q, Sum

from apps.closing.selectors import resolve_report_exercise_context
from apps.companies.models import Company
from apps.journal.models import JournalEntryLine
from apps.reports import cache as report_cache
from apps.reports.exercise_context import (
    attach_report_exercise_metadata,
    build_report_exercise_cache_parts,
)

_ZERO = Decimal("0")


def _balance_pair(total_debit: Decimal, total_credit: Decimal) -> tuple[str | None, str | None]:
    """Return saldo deudor/acreedor representation for a row or subtotal."""
    net = total_debit - total_credit
    if net > _ZERO:
        return f"{net:.2f}", None
    if net < _ZERO:
        return None, f"{-net:.2f}"
    return None, None


def get_trial_balance(
    *,
    company: Company,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
) -> dict:
    """Balance de Comprobación: grouped subtotals (colectivas) + movement accounts."""
    context = resolve_report_exercise_context(
        company=company,
        date_from=date_from,
        date_to=date_to,
    )
    actual_date_to = context.computed_to
    cache_extra_parts = build_report_exercise_cache_parts(context=context)
    cached = report_cache.get_cached_report(
        report_name="trial_balance",
        company_id=company.id,
        date_from=context.computed_from,
        date_to=actual_date_to,
        extra_parts=cache_extra_parts,
    )
    if cached is not None:
        return attach_report_exercise_metadata(report=cached, context=context)

    line_filter = Q(
        account__company_account__company=company,
        journal_entry__company=company,
        journal_entry__date__lte=actual_date_to,
    )
    if context.computed_from:
        line_filter &= Q(journal_entry__date__gte=context.computed_from)

    rows = list(
        JournalEntryLine.objects.filter(line_filter)
        .values(
            "account_id",
            "account__full_code",
            "account__name",
            "account__type",
            "account__parent_id",
            "account__parent__full_code",
            "account__parent__name",
            "account__parent__type",
        )
        .annotate(
            total_debit=Sum("amount", filter=Q(type=JournalEntryLine.LineType.DEBIT)),
            total_credit=Sum("amount", filter=Q(type=JournalEntryLine.LineType.CREDIT)),
        )
        .order_by("account__full_code")
    )

    if context.computed_from:
        actual_date_from = context.computed_from
    elif rows:
        first_date = (
            JournalEntryLine.objects.filter(
                account__company_account__company=company,
                journal_entry__company=company,
            )
            .order_by("journal_entry__date")
            .values_list("journal_entry__date", flat=True)
            .first()
        )
        actual_date_from = first_date or actual_date_to
    else:
        actual_date_from = actual_date_to

    if not rows:
        report = {
            "company_id": company.id,
            "company": company.name,
            "date_from": str(actual_date_from),
            "date_to": str(actual_date_to),
            "grand_total_debit": "0.00",
            "grand_total_credit": "0.00",
            "groups": [],
            "totals": {
                "total_debit": "0.00",
                "total_credit": "0.00",
                "total_debit_balance": "0.00",
                "total_credit_balance": "0.00",
            },
        }
        report_cache.set_cached_report(
            report_name="trial_balance",
            company_id=company.id,
            date_from=context.computed_from,
            date_to=actual_date_to,
            extra_parts=cache_extra_parts,
            value=report,
            is_demo=company.is_demo,
        )
        return attach_report_exercise_metadata(report=report, context=context)

    groups: dict[int, dict] = {}
    grand_debit = _ZERO
    grand_credit = _ZERO

    for row in rows:
        total_debit = row["total_debit"] or _ZERO
        total_credit = row["total_credit"] or _ZERO
        debit_balance, credit_balance = _balance_pair(total_debit, total_credit)

        account_data = {
            "account_code": row["account__full_code"],
            "account_name": row["account__name"],
            "account_type": row["account__type"],
            "total_debit": f"{total_debit:.2f}",
            "total_credit": f"{total_credit:.2f}",
            "debit_balance": debit_balance,
            "credit_balance": credit_balance,
        }

        parent_id = row["account__parent_id"]
        if parent_id not in groups:
            groups[parent_id] = {
                "account_code": row["account__parent__full_code"],
                "account_name": row["account__parent__name"],
                "account_type": row["account__parent__type"],
                "_subtotal_debit": _ZERO,
                "_subtotal_credit": _ZERO,
                "accounts": [],
            }

        groups[parent_id]["_subtotal_debit"] += total_debit
        groups[parent_id]["_subtotal_credit"] += total_credit
        groups[parent_id]["accounts"].append(account_data)

        grand_debit += total_debit
        grand_credit += total_credit

    grand_debit_balance = _ZERO
    grand_credit_balance = _ZERO
    groups_data = []

    for group in groups.values():
        sub_debit = group["_subtotal_debit"]
        sub_credit = group["_subtotal_credit"]
        sub_net = sub_debit - sub_credit
        sub_debit_balance, sub_credit_balance = _balance_pair(sub_debit, sub_credit)

        grand_debit_balance += max(sub_net, _ZERO)
        grand_credit_balance += max(-sub_net, _ZERO)

        groups_data.append(
            {
                "account_code": group["account_code"],
                "account_name": group["account_name"],
                "account_type": group["account_type"],
                "subtotal_debit": f"{sub_debit:.2f}",
                "subtotal_credit": f"{sub_credit:.2f}",
                "subtotal_debit_balance": sub_debit_balance,
                "subtotal_credit_balance": sub_credit_balance,
                "accounts": group["accounts"],
            }
        )

    groups_data.sort(key=lambda g: g["account_code"] or "")

    report = {
        "company_id": company.id,
        "company": company.name,
        "date_from": str(actual_date_from),
        "date_to": str(actual_date_to),
        "grand_total_debit": f"{grand_debit:.2f}",
        "grand_total_credit": f"{grand_credit:.2f}",
        "groups": groups_data,
        "totals": {
            "total_debit": f"{grand_debit:.2f}",
            "total_credit": f"{grand_credit:.2f}",
            "total_debit_balance": f"{grand_debit_balance:.2f}",
            "total_credit_balance": f"{grand_credit_balance:.2f}",
        },
    }
    report_cache.set_cached_report(
        report_name="trial_balance",
        company_id=company.id,
        date_from=context.computed_from,
        date_to=actual_date_to,
        extra_parts=cache_extra_parts,
        value=report,
        is_demo=company.is_demo,
    )
    return attach_report_exercise_metadata(report=report, context=context)
