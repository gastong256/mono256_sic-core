from __future__ import annotations

import time
from collections.abc import Callable

import structlog
from django.conf import settings
from django.http import HttpRequest, HttpResponse

logger = structlog.get_logger("http")


class RequestLoggingMiddleware:
    """Emit structured logs for every HTTP request and flag slow responses."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.enabled = settings.REQUEST_LOG_ENABLED
        self.slow_threshold_ms = settings.SLOW_REQUEST_THRESHOLD_MS
        self.skip_paths = set(settings.REQUEST_LOG_SKIP_PATHS)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not self.enabled or request.path in self.skip_paths:
            return self.get_response(request)

        started = time.perf_counter()
        try:
            response = self.get_response(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.exception("request_failed", **self._build_log_fields(request, 500, duration_ms))
            raise

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        fields = self._build_log_fields(request, response.status_code, duration_ms)
        if duration_ms >= self.slow_threshold_ms:
            logger.warning("slow_request", slow_threshold_ms=self.slow_threshold_ms, **fields)
        else:
            logger.info("request_completed", **fields)
        return response

    @staticmethod
    def _build_log_fields(
        request: HttpRequest,
        status_code: int,
        duration_ms: float,
    ) -> dict[str, object]:
        fields: dict[str, object] = {
            "method": request.method,
            "path": request.path,
            "status_code": status_code,
            "duration_ms": duration_ms,
        }
        user = getattr(request, "user", None)
        if getattr(user, "is_authenticated", False):
            fields["user_id"] = user.id
            fields["user_role"] = getattr(user, "role", "")
        return fields
