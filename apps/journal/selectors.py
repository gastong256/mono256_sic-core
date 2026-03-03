from django.db.models import QuerySet
from rest_framework.exceptions import NotFound

from apps.companies.models import Company
from apps.journal.models import JournalEntry


def list_journal_entries(*, company: Company) -> QuerySet[JournalEntry]:
    return (
        JournalEntry.objects.filter(company=company)
        .select_related("created_by", "reversal_of", "reversed_by")
        .prefetch_related("lines")
        .order_by("entry_number")
    )


def get_journal_entry(*, pk: int, company: Company) -> JournalEntry:
    try:
        return (
            JournalEntry.objects.select_related("created_by", "reversal_of", "reversed_by")
            .prefetch_related("lines__account")
            .get(pk=pk, company=company)
        )
    except JournalEntry.DoesNotExist:
        raise NotFound(detail="Asiento contable no encontrado.")
