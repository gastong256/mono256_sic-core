from django.urls import path

from apps.reports.views import JournalBookView, LedgerView, TrialBalanceView

app_name = "reports"

urlpatterns = [
    path(
        "companies/<int:company_id>/reports/journal-book/",
        JournalBookView.as_view(),
        name="journal-book",
    ),
    path(
        "companies/<int:company_id>/reports/ledger/",
        LedgerView.as_view(),
        name="ledger",
    ),
    path(
        "companies/<int:company_id>/reports/trial-balance/",
        TrialBalanceView.as_view(),
        name="trial-balance",
    ),
]
