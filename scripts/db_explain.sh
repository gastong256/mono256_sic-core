#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <company_id>"
  exit 1
fi

COMPANY_ID="$1"
PYTHON_BIN="./.venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python"
fi

DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.local}" "$PYTHON_BIN" - <<PY
import datetime
import os

import django
from django.db.models import Q, Sum

os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.getenv("DJANGO_SETTINGS_MODULE", "config.settings.local"))
django.setup()

from apps.journal.models import JournalEntry, JournalEntryLine

company_id = int("${COMPANY_ID}")
today = datetime.date.today()
date_from = today - datetime.timedelta(days=365)

print("\\n--- EXPLAIN: journal list by company/date/entry_number ---")
journal_qs = (
    JournalEntry.objects.filter(company_id=company_id, date__gte=date_from, date__lte=today)
    .order_by("date", "entry_number")
)
print(journal_qs.explain())

print("\\n--- EXPLAIN: ledger movements grouped/filter by account + journal range ---")
ledger_qs = (
    JournalEntryLine.objects.filter(
        account__company_account__company_id=company_id,
        journal_entry__company_id=company_id,
        journal_entry__date__gte=date_from,
        journal_entry__date__lte=today,
    )
    .values("account_id")
    .annotate(
        debit_sum=Sum("amount", filter=Q(type=JournalEntryLine.LineType.DEBIT)),
        credit_sum=Sum("amount", filter=Q(type=JournalEntryLine.LineType.CREDIT)),
    )
    .order_by("account_id")
)
print(ledger_qs.explain())
PY
