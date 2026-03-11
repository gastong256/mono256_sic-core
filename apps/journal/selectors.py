from decimal import Decimal

from django.db.models import DecimalField, Q, QuerySet, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework.exceptions import NotFound

from apps.companies.models import Company
from apps.journal.models import JournalEntry, JournalEntryLine


def _with_totals(qs: QuerySet[JournalEntry]) -> QuerySet[JournalEntry]:
    amount_field = DecimalField(max_digits=15, decimal_places=2)
    zero = Value(Decimal("0.00"), output_field=amount_field)
    return qs.annotate(
        total_debit=Coalesce(
            Sum("lines__amount", filter=Q(lines__type=JournalEntryLine.LineType.DEBIT)),
            zero,
            output_field=amount_field,
        ),
        total_credit=Coalesce(
            Sum("lines__amount", filter=Q(lines__type=JournalEntryLine.LineType.CREDIT)),
            zero,
            output_field=amount_field,
        ),
    )


def list_journal_entries(*, company: Company) -> QuerySet[JournalEntry]:
    base_qs = (
        JournalEntry.objects.filter(company=company)
        .select_related("created_by", "reversal_of", "reversed_by")
        .order_by("entry_number")
    )
    return _with_totals(base_qs)


def get_journal_entry(*, pk: int, company: Company) -> JournalEntry:
    try:
        qs = (
            JournalEntry.objects.select_related("created_by", "reversal_of", "reversed_by")
            .prefetch_related("lines__account")
        )
        return _with_totals(qs).get(pk=pk, company=company)
    except JournalEntry.DoesNotExist:
        raise NotFound(detail="Asiento contable no encontrado.")
