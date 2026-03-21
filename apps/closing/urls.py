from django.urls import path

from apps.closing.api.views import (
    ClosingExecuteView,
    ClosingPreviewView,
    ClosingSnapshotDetailView,
    ClosingStateView,
    CurrentBookBalancesView,
    LatestClosingSnapshotView,
    LogicalExerciseListView,
)

app_name = "closing"

urlpatterns = [
    path(
        "companies/<int:company_id>/logical-exercises/",
        LogicalExerciseListView.as_view(),
        name="logical-exercises",
    ),
    path(
        "companies/<int:company_id>/closing/state/",
        ClosingStateView.as_view(),
        name="state",
    ),
    path(
        "companies/<int:company_id>/closing/current-balances/",
        CurrentBookBalancesView.as_view(),
        name="current-balances",
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
    path(
        "companies/<int:company_id>/closing/latest-snapshot/",
        LatestClosingSnapshotView.as_view(),
        name="latest-snapshot",
    ),
    path(
        "companies/<int:company_id>/closing/snapshots/<int:snapshot_id>/",
        ClosingSnapshotDetailView.as_view(),
        name="snapshot-detail",
    ),
]
