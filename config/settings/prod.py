from .base import *  # noqa: F401, F403
from .base import SECRET_KEY, env

_UNSAFE_DEFAULTS = {
    "unsafe-default-do-not-use-in-production",
    "@qUUwZMC07hBh__DJANGO_SECRET_KEY__404aTm#HbUfcgtj__DJANGO_SECRET_KEY__zrUqWB%Q4lWOKhranF@X",
    "",
}
if not SECRET_KEY or SECRET_KEY in _UNSAFE_DEFAULTS:
    raise RuntimeError(
        "DJANGO_SECRET_KEY is not set or still contains an unsafe placeholder. "
        "Set a real secret key via the DJANGO_SECRET_KEY environment variable."
    )

DEBUG = False

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
