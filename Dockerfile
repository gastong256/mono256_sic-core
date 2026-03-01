# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.12

# ── builder ───────────────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir uv==0.4.*

COPY pyproject.toml .
# Sync only production deps (no dev extras)
RUN uv sync --no-dev --no-install-project

# ── runtime ───────────────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

COPY --from=builder /build/.venv .venv

COPY apps/ apps/
COPY config/ config/
COPY manage.py .

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE __PORT__

CMD ["gunicorn", \
     "--bind", "0.0.0.0:__PORT__", \
     "--workers", "2", \
     "--worker-class", "sync", \
     "--timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "config.wsgi:application"]
