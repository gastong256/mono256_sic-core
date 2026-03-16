# Observability

## Structured Logging

Logs are emitted via [structlog](https://www.structlog.org/) to stdout.

- **Local dev**: colorized console output (`JSON_LOGS=false`).
- **Production / CI**: JSON lines (`JSON_LOGS=true`).

Every log record automatically includes:

| Field        | Source                             |
|--------------|------------------------------------|
| `request_id` | `RequestIDMiddleware` + ContextVar |
| `tenant_id`  | `TenantMiddleware` + ContextVar    |
| `timestamp`  | ISO 8601 UTC                       |
| `level`      | Log level string                   |
| `logger`     | Module name                        |

### Emitting logs in application code

```python
import structlog

logger = structlog.get_logger(__name__)

def my_service_function(item_id: str) -> None:
    logger.info("processing_item", item_id=item_id)
    # ...
    logger.warning("item_not_found", item_id=item_id)
```

Always use keyword arguments; avoid f-strings in log messages.

## HTTP Request Logs

`RequestLoggingMiddleware` emits one structured log per HTTP request with:

- `method`
- `path`
- `status_code`
- `duration_ms`
- `user_id` and `user_role` (when authenticated)

Slow requests are marked with event `slow_request` when `duration_ms >= SLOW_REQUEST_THRESHOLD_MS`.
Unhandled exceptions produce `request_failed` with stack trace.

Configuration:

```env
REQUEST_LOG_ENABLED=true
SLOW_REQUEST_THRESHOLD_MS=1000
REQUEST_LOG_SKIP_PATHS=/healthz,/readyz
```

`REQUEST_LOG_SKIP_PATHS` should include high-frequency probes to reduce log noise.

## Request ID

`RequestIDMiddleware` (see `config/middleware/request_id.py`):

- Reads `X-Request-ID` from the incoming request.
- Generates a UUIDv4 if absent.
- Stores it in a `ContextVar` so it flows into structlog automatically.
- Returns it as `X-Request-ID` in every response.

Clients can supply a request ID for distributed tracing correlation (e.g. from an API gateway).

## OpenTelemetry (optional)

OTel tracing is disabled by default. To enable it:

1. Install optional deps:
   ```bash
   uv sync --extra otel
   ```

2. Set environment variables:
   ```env
   OTEL_ENABLED=true
   OTEL_SERVICE_NAME=my-service
   OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
   ```

3. Restart the service. Django and psycopg will be auto-instrumented.

The setup is in `config/otel.py` and is a no-op when disabled — no import errors if OTel packages are absent.

## Health Endpoints

| Endpoint  | Purpose                  | Checks DB | Checks Redis |
|-----------|--------------------------|-----------|--------------|
| `GET /healthz` | Liveness — process alive | No | No |
| `GET /readyz`  | Readiness — ready to serve traffic | Yes | Yes, when `REDIS_URL` is configured |

`readyz` returns:

```json
{
  "status": "ok",
  "db": true,
  "redis": true,
  "fallback": false
}
```

Status semantics:
- `ok`: DB is healthy and Redis is healthy, or Redis is not configured.
- `degraded`: DB is healthy but Redis is configured and unavailable; the app is serving traffic with fallback behavior.
- `unavailable`: DB is unavailable.

Use `readyz` in Kubernetes `readinessProbe` and `healthz` in `livenessProbe`.

## Log Level Configuration

Set via `LOG_LEVEL` env var (default `INFO`).

```env
LOG_LEVEL=DEBUG   # verbose, local dev
LOG_LEVEL=INFO    # production default
LOG_LEVEL=WARNING # quieter
```

## Shared Cache for Security Controls

Registration anti-abuse controls (rate limits and cooldowns) use Django cache.

- **Local/dev fallback**: in-memory cache (`LocMemCache`)
- **Production**: configure a shared Redis cache via `REDIS_URL`

```env
REDIS_URL=redis://cache-host:6379/0
```

Without a shared cache in production, limits may become inconsistent across multiple processes/instances.

If Redis becomes unavailable in production:
- report/chart/visibility caches degrade to recalculation from the primary data source
- registration code generation/validation continues because the source of truth is the database
- temporary anti-abuse counters may degrade and become less strict until Redis is available again
