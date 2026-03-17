from django.urls import path

from apps.closing.api.views import ClosingExecuteView, ClosingPreviewView, ClosingStateView

app_name = "closing"

urlpatterns = [
    path(
        "companies/<int:company_id>/closing/state/",
        ClosingStateView.as_view(),
        name="state",
    ),
    path(
        "companies/<int:company_id>/closing/preview/",
        ClosingPreviewView.as_view(),
        name="preview",
    ),
    path(
        "companies/<int:company_id>/closing/execute/",
        ClosingExecuteView.as_view(),
        name="execute",
    ),
]
