from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from config.middleware.tenant import TenantMiddleware


def _ok_response(request):
    return HttpResponse("ok")


def test_tenant_middleware_accepts_valid_tenant_id():
    request = RequestFactory().get("/", HTTP_X_TENANT_ID="tenant-1")
    middleware = TenantMiddleware(_ok_response)
    middleware(request)
    assert request.tenant_id == "tenant-1"


def test_tenant_middleware_falls_back_for_invalid_tenant_id():
    request = RequestFactory().get("/", HTTP_X_TENANT_ID="BAD TENANT!")
    middleware = TenantMiddleware(_ok_response)
    middleware(request)
    assert request.tenant_id == "public"


@override_settings(TENANT_ALLOWED_IDS=["tenant-a"])
def test_tenant_middleware_uses_allowlist_when_configured():
    request = RequestFactory().get("/", HTTP_X_TENANT_ID="tenant-b")
    middleware = TenantMiddleware(_ok_response)
    middleware(request)
    assert request.tenant_id == "public"
