from django.urls import path

from apps.accounts.api.views import (
    CompanyAccountDetailView,
    CompanyAccountListCreateView,
    GlobalChartView,
)

app_name = "accounts"

urlpatterns = [
    path("accounts/chart/", GlobalChartView.as_view(), name="chart"),
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
