# ADR 0002: Multitenancy Strategy

**Status:** Accepted
**Date:** 2024-01-01

## Context

The service may need to serve multiple tenants from a single deployment. We need a strategy that is lightweight enough not to impede single-tenant deployments but extensible enough to support true data isolation when required.

## Decision

We adopt a **header-based tenant resolution** approach as the initial hook:

1. `TenantMiddleware` reads the `X-Tenant-ID` request header.
2. If absent, `tenant_id` defaults to `"public"`.
3. `tenant_id` is stored in a `ContextVar` so it is accessible throughout the request lifecycle — in log records, service layer functions, and future query filters — without being passed explicitly.

This is intentionally lightweight. No row-level security or schema-per-tenant isolation is implemented at this layer. Teams adopting multitenancy at the data layer should extend this foundation with one of:

- **Shared schema + tenant column**: Add a `tenant_id` FK/field to models and use a global queryset filter (Django managers or a middleware-driven queryset mixin).
- **Schema-per-tenant**: Use `django-tenants` or a custom PostgreSQL `SET search_path` approach per request.
- **Database-per-tenant**: Dynamically route `DATABASES` based on the resolved `tenant_id`.

## Consequences

- All log records include `tenant_id` at zero overhead.
- Single-tenant deployments see `tenant_id = "public"` everywhere and can ignore the mechanism.
- The `X-Tenant-ID` header must be treated as **untrusted user input** and validated against an allowlist before use in any security-sensitive decision. The current implementation passes it through raw; production multitenancy must add validation.
- API gateways or service meshes should be responsible for injecting a verified `X-Tenant-ID` header.
