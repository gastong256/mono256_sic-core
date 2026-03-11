# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.12

# ── builder ───────────────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir uv==0.10.*

COPY pyproject.toml uv.lock ./
# Sync production deps from lockfile without building/installing the local package.
RUN uv sync --frozen --no-dev --no-install-project

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
COPY scripts/run_gunicorn.sh scripts/run_gunicorn.sh
COPY scripts/run_migrations.sh scripts/run_migrations.sh
COPY manage.py .

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

CMD ["/app/scripts/run_gunicorn.sh"]
