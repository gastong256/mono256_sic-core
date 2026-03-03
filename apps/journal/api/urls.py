from django.urls import path

from apps.journal.api.views import JournalEntryDetailView, JournalEntryListCreateView

app_name = "journal"

urlpatterns = [
    path(
        "companies/<int:company_id>/journal/",
        JournalEntryListCreateView.as_view(),
        name="journal-list",
    ),
    path(
        "companies/<int:company_id>/journal/<int:entry_id>/",
        JournalEntryDetailView.as_view(),
        name="journal-detail",
    ),
]
