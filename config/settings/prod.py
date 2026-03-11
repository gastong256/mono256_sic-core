from .base import *  # noqa: F401, F403
from .base import ALLOWED_HOSTS, REDIS_URL, SECRET_KEY, env

_UNSAFE_DEFAULTS = {
    "unsafe-default-do-not-use-in-production",
    "change-me",
    "@qUUwZMC07hBh__DJANGO_SECRET_KEY__404aTm#HbUfcgtj__DJANGO_SECRET_KEY__zrUqWB%Q4lWOKhranF@X",
    "",
}
if not SECRET_KEY or SECRET_KEY in _UNSAFE_DEFAULTS:
    raise RuntimeError(
        "DJANGO_SECRET_KEY is not set or still contains an unsafe placeholder. "
        "Set a real secret key via the DJANGO_SECRET_KEY environment variable."
    )

if set(ALLOWED_HOSTS).issubset({"localhost", "127.0.0.1", "0.0.0.0"}):
    raise RuntimeError(
        "DJANGO_ALLOWED_HOSTS is using local-only defaults. "
        "Set real production hosts via DJANGO_ALLOWED_HOSTS."
    )

DEBUG = False

if not REDIS_URL:
    raise RuntimeError(
        "REDIS_URL is required in production. "
        "A shared cache is required for consistent throttling and cache behavior."
    )

USE_X_FORWARDED_HOST = env.bool("USE_X_FORWARDED_HOST", default=True)
if env.bool("USE_X_FORWARDED_PROTO", default=True):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=True)
SECURE_CONTENT_TYPE_NOSNIFF = env.bool("SECURE_CONTENT_TYPE_NOSNIFF", default=True)
SECURE_REFERRER_POLICY = env("SECURE_REFERRER_POLICY", default="same-origin")
X_FRAME_OPTIONS = env("X_FRAME_OPTIONS", default="DENY")

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = env("SESSION_COOKIE_SAMESITE", default="Lax")
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = env("CSRF_COOKIE_SAMESITE", default="Lax")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

ENABLE_ADMIN_SITE = env.bool("ENABLE_ADMIN_SITE", default=False)
ENABLE_API_DOCS = env.bool("ENABLE_API_DOCS", default=False)
ENABLE_EXAMPLE_API = env.bool("ENABLE_EXAMPLE_API", default=False)
