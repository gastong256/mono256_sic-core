from django.contrib import admin
from django.urls import include, path
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

_status_response = inline_serializer(
    name="StatusResponse",
    fields={"status": serializers.CharField()},
)


class LivenessView(APIView):
    @extend_schema(
        operation_id="liveness",
        summary="Liveness probe",
        responses={200: _status_response},
        tags=["health"],
    )
    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})


class ReadinessView(APIView):
    @extend_schema(
        operation_id="readiness",
        summary="Readiness probe",
        responses={
            200: _status_response,
            503: OpenApiResponse(description="Database unavailable"),
        },
        tags=["health"],
    )
    def get(self, request: Request) -> Response:
        from django.db import connection

        try:
            connection.ensure_connection()
        except Exception as exc:
            return Response({"status": "unavailable", "detail": str(exc)}, status=503)

        return Response({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", LivenessView.as_view(), name="liveness"),
    path("readyz", ReadinessView.as_view(), name="readiness"),
    # OpenAPI
    path("api/openapi.json", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # Versioned API
    path("api/v1/", include("apps.example.api.urls")),
    path("api/v1/auth/", include("apps.users.api.urls", namespace="users")),
    path("api/v1/admin/", include("apps.users.api.admin_urls")),
    path("api/v1/teacher/", include("apps.users.api.teacher_urls")),
    path("api/v1/", include("apps.courses.api.urls", namespace="courses")),
    path("api/v1/", include("apps.companies.api.urls", namespace="companies")),
    path("api/v1/", include("apps.accounts.api.urls", namespace="accounts")),
    path("api/v1/", include("apps.journal.api.urls", namespace="journal")),
    path("api/v1/", include("apps.reports.urls", namespace="reports")),
]
