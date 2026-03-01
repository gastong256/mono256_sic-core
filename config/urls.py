from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class LivenessView(APIView):
    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})


class ReadinessView(APIView):
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
]
