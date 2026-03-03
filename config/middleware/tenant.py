from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from config.context import tenant_id_var

TENANT_HEADER = "HTTP_X_TENANT_ID"
DEFAULT_TENANT = "public"


class TenantMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        tenant_id = request.META.get(TENANT_HEADER, DEFAULT_TENANT) or DEFAULT_TENANT
        tenant_id_var.set(tenant_id)
        request.tenant_id = tenant_id  # type: ignore[attr-defined]
        return self.get_response(request)
