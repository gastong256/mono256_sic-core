from typing import Any

from rest_framework import exceptions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def _get_error_code(exc: Exception) -> str:
    if hasattr(exc, "default_code"):
        return str(exc.default_code)  # type: ignore[attr-defined]
    return exc.__class__.__name__.lower()


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, exceptions.ValidationError):
        code = "validation_error"
        message = "Invalid input."
        detail: Any = response.data
    elif isinstance(exc, exceptions.NotFound):
        code = "not_found"
        message = str(exc.detail) if hasattr(exc, "detail") else "Not found."
        detail = None
    elif isinstance(exc, exceptions.AuthenticationFailed):
        code = "authentication_failed"
        message = str(exc.detail) if hasattr(exc, "detail") else "Authentication failed."
        detail = None
    elif isinstance(exc, exceptions.PermissionDenied):
        code = "permission_denied"
        message = str(exc.detail) if hasattr(exc, "detail") else "Permission denied."
        detail = None
    else:
        code = _get_error_code(exc)
        message = str(getattr(exc, "detail", str(exc)))
        detail = None

    response.data = {
        "error": {
            "code": code,
            "message": message,
            "detail": detail,
        }
    }
    return response


def _request_handler(request: Request, exc: Exception) -> Response:
    """Handler for non-DRF 500s raised inside views."""
    return Response(
        {"error": {"code": "internal_error", "message": "An unexpected error occurred.", "detail": None}},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
