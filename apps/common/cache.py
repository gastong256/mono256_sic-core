import structlog
from django.core.cache import cache

logger = structlog.get_logger(__name__)


def safe_cache_get(key: str, default=None):
    try:
        return cache.get(key, default)
    except Exception:
        logger.warning("cache_get_failed", key=key)
        return default


def safe_cache_set(key: str, value, *, timeout: int | None = None) -> bool:
    try:
        cache.set(key, value, timeout=timeout)
    except Exception:
        logger.warning("cache_set_failed", key=key)
        return False
    return True


def safe_cache_delete(key: str) -> bool:
    try:
        cache.delete(key)
    except Exception:
        logger.warning("cache_delete_failed", key=key)
        return False
    return True


def safe_cache_add(key: str, value, *, timeout: int | None = None) -> bool | None:
    try:
        return bool(cache.add(key, value, timeout=timeout))
    except Exception:
        logger.warning("cache_add_failed", key=key)
        return None


def safe_cache_incr(key: str, delta: int = 1) -> int | None:
    try:
        return int(cache.incr(key, delta))
    except Exception:
        logger.warning("cache_incr_failed", key=key)
        return None


def cache_roundtrip_ok(*, key: str, value, timeout: int = 5) -> bool:
    try:
        cache.set(key, value, timeout=timeout)
        return cache.get(key) == value
    except Exception:
        logger.warning("cache_roundtrip_failed", key=key)
        return False
