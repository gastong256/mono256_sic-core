import re
from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from config.context import tenant_id_var

TENANT_HEADER = "HTTP_X_TENANT_ID"
DEFAULT_TENANT = "public"
_TENANT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class TenantMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.allowed_tenants = set(getattr(settings, "TENANT_ALLOWED_IDS", []))

    def _resolve_tenant_id(self, raw_tenant_id: str | None) -> str:
        tenant_id = (raw_tenant_id or DEFAULT_TENANT).strip().lower()
        if not _TENANT_ID_RE.fullmatch(tenant_id):
            return DEFAULT_TENANT
        if self.allowed_tenants and tenant_id not in self.allowed_tenants:
            return DEFAULT_TENANT
        return tenant_id

    def __call__(self, request: HttpRequest) -> HttpResponse:
        tenant_id = self._resolve_tenant_id(request.META.get(TENANT_HEADER))
        tenant_id_var.set(tenant_id)
        request.tenant_id = tenant_id  # type: ignore[attr-defined]
        return self.get_response(request)
