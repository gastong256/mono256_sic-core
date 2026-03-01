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

| Endpoint  | Purpose                  | Checks DB |
|-----------|--------------------------|-----------|
| `GET /healthz` | Liveness — process alive | No |
| `GET /readyz`  | Readiness — ready to serve traffic | Yes |

Use `readyz` in Kubernetes `readinessProbe` and `healthz` in `livenessProbe`.

## Log Level Configuration

Set via `LOG_LEVEL` env var (default `INFO`).

```env
LOG_LEVEL=DEBUG   # verbose, local dev
LOG_LEVEL=INFO    # production default
LOG_LEVEL=WARNING # quieter
```
