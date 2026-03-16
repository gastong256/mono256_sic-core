import structlog
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.cache import cache_roundtrip_ok

_liveness_response = inline_serializer(
    name="LivenessResponse",
    fields={"status": serializers.CharField()},
)
_readiness_response = inline_serializer(
    name="ReadinessResponse",
    fields={
        "status": serializers.CharField(),
        "db": serializers.BooleanField(),
        "redis": serializers.BooleanField(),
        "fallback": serializers.BooleanField(),
    },
)
logger = structlog.get_logger(__name__)


class LivenessView(APIView):
    @extend_schema(
        operation_id="liveness",
        summary="Liveness probe",
        responses={200: _liveness_response},
        tags=["health"],
    )
    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})


class ReadinessView(APIView):
    @staticmethod
    def _check_db() -> bool:
        from django.db import connection

        try:
            connection.ensure_connection()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            logger.exception("readiness_db_check_failed")
            return False

        return True

    @staticmethod
    def _check_redis() -> bool:
        if not settings.REDIS_URL:
            return False

        return cache_roundtrip_ok(key="__readyz__", value="ok", timeout=5)

    @extend_schema(
        operation_id="readiness",
        summary="Readiness probe",
        responses={
            200: _readiness_response,
            503: OpenApiResponse(description="Required dependencies unavailable"),
        },
        tags=["health"],
    )
    def get(self, request: Request) -> Response:
        db_ok = self._check_db()
        redis_ok = self._check_redis()
        fallback_active = bool(settings.REDIS_URL) and not redis_ok and db_ok

        if not db_ok:
            status_value = "unavailable"
            status_code = 503
        elif fallback_active:
            status_value = "degraded"
            status_code = 200
        else:
            status_value = "ok"
            status_code = 200

        return Response(
            {
                "status": status_value,
                "db": db_ok,
                "redis": redis_ok,
                "fallback": fallback_active,
            },
            status=status_code,
        )


urlpatterns = [
    path("healthz", LivenessView.as_view(), name="liveness"),
    path("readyz", ReadinessView.as_view(), name="readiness"),
]

if settings.ENABLE_ADMIN_SITE:
    urlpatterns.append(path("admin/", admin.site.urls))

if settings.ENABLE_API_DOCS:
    urlpatterns.extend(
        [
            path("api/openapi.json", SpectacularAPIView.as_view(), name="schema"),
            path("api/docs", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
            path("api/redoc", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
        ]
    )

if settings.ENABLE_EXAMPLE_API:
    urlpatterns.append(path("api/v1/", include("apps.example.api.urls")))

urlpatterns.extend(
    [
        path("api/v1/auth/", include("apps.users.api.urls", namespace="users")),
        path("api/v1/admin/", include("apps.users.api.admin_urls")),
        path("api/v1/teacher/", include("apps.users.api.teacher_urls")),
        path("api/v1/", include("apps.courses.api.urls", namespace="courses")),
        path("api/v1/", include("apps.companies.api.urls", namespace="companies")),
        path("api/v1/", include("apps.accounts.api.urls", namespace="accounts")),
        path("api/v1/", include("apps.journal.api.urls", namespace="journal")),
        path("api/v1/", include("apps.reports.urls", namespace="reports")),
    ]
)
