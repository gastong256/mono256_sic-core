import datetime

from django.conf import settings

from apps.common.cache import safe_cache_add, safe_cache_get, safe_cache_incr, safe_cache_set

_VERSION_TTL_SECONDS = 30 * 24 * 60 * 60


def _cache_timeout() -> int:
    return int(getattr(settings, "REPORT_CACHE_TIMEOUT", 120))


def _company_report_version_key(company_id: int) -> str:
    return f"reports:company:{company_id}:version"


def _get_or_init_version(key: str) -> int:
    current = safe_cache_get(key)
    if isinstance(current, int) and current > 0:
        return current
    safe_cache_set(key, 1, timeout=_VERSION_TTL_SECONDS)
    return 1


def _bump_version(key: str) -> int:
    if safe_cache_add(key, 2, timeout=_VERSION_TTL_SECONDS) is True:
        return 2

    value = safe_cache_incr(key)
    if value is None:
        current = safe_cache_get(key)
        if not isinstance(current, int):
            value = 2
        else:
            value = current + 1
        safe_cache_set(key, value, timeout=_VERSION_TTL_SECONDS)
    return int(value)


def report_cache_version(*, company_id: int) -> int:
    return _get_or_init_version(_company_report_version_key(company_id))


def bump_report_cache_version(*, company_id: int) -> None:
    _bump_version(_company_report_version_key(company_id))


def _normalize_date_to(date_to: datetime.date | None) -> datetime.date:
    return date_to or datetime.date.today()


def _normalize_part(value) -> str:
    if value is None:
        return "none"
    if isinstance(value, datetime.date):
        return value.isoformat()
    return str(value)


def build_report_cache_key(
    *,
    report_name: str,
    company_id: int,
    date_from: datetime.date | None,
    date_to: datetime.date | None,
    extra_parts: dict[str, object] | None = None,
) -> str:
    version = report_cache_version(company_id=company_id)
    parts = [
        "reports",
        report_name,
        f"company:{company_id}",
        f"from:{_normalize_part(date_from)}",
        f"to:{_normalize_part(_normalize_date_to(date_to))}",
        f"v:{version}",
    ]
    for key, value in sorted((extra_parts or {}).items()):
        parts.append(f"{key}:{_normalize_part(value)}")
    return ":".join(parts)


def get_cached_report(
    *,
    report_name: str,
    company_id: int,
    date_from: datetime.date | None,
    date_to: datetime.date | None,
    extra_parts: dict[str, object] | None = None,
):
    key = build_report_cache_key(
        report_name=report_name,
        company_id=company_id,
        date_from=date_from,
        date_to=date_to,
        extra_parts=extra_parts,
    )
    return safe_cache_get(key)


def set_cached_report(
    *,
    report_name: str,
    company_id: int,
    date_from: datetime.date | None,
    date_to: datetime.date | None,
    value,
    extra_parts: dict[str, object] | None = None,
) -> None:
    key = build_report_cache_key(
        report_name=report_name,
        company_id=company_id,
        date_from=date_from,
        date_to=date_to,
        extra_parts=extra_parts,
    )
    safe_cache_set(key, value, timeout=_cache_timeout())
