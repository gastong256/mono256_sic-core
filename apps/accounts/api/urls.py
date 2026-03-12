from django.urls import path

from apps.accounts.api.views import (
    CompanyAccountDetailView,
    CompanyAccountListCreateView,
    GlobalChartView,
    TeacherAccountVisibilityBatchUpdateView,
    TeacherAccountVisibilityDetailView,
    TeacherAccountVisibilityListView,
)

app_name = "accounts"

urlpatterns = [
    path("accounts/chart/", GlobalChartView.as_view(), name="chart"),
    path(
        "accounts/visibility/",
        TeacherAccountVisibilityListView.as_view(),
        name="account-visibility",
    ),
    path(
        "accounts/visibility/batch/",
        TeacherAccountVisibilityBatchUpdateView.as_view(),
        name="account-visibility-batch",
    ),
    path(
        "accounts/visibility/<int:account_id>/",
        TeacherAccountVisibilityDetailView.as_view(),
        name="account-visibility-detail",
    ),
    path(
        "accounts/company/<int:company_id>/",
        CompanyAccountListCreateView.as_view(),
        name="company-accounts",
    ),
    path(
        "accounts/company/<int:company_id>/<int:account_id>/",
        CompanyAccountDetailView.as_view(),
        name="company-account-detail",
    ),
]
