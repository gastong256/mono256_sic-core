import uuid
from collections.abc import Callable
from typing import Any

from django.http import HttpRequest, HttpResponse

from config.context import request_id_var

REQUEST_ID_HEADER = "HTTP_X_REQUEST_ID"
RESPONSE_HEADER = "X-Request-ID"


class RequestIDMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.META.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request_id_var.set(request_id)
        request.request_id = request_id  # type: ignore[attr-defined]

        response = self.get_response(request)
        response[RESPONSE_HEADER] = request_id
        return response
