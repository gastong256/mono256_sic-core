from pathlib import Path

from .base import *  # noqa: F401, F403
from .base import env

SECRET_KEY = "test-secret-key-not-for-production"  # noqa: S105

DEBUG = False

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://postgres:postgres@localhost:5432/sic_core_test",
    ),
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
STATIC_ROOT = Path(__file__).resolve().parent.parent.parent / ".staticfiles-test"
STATIC_ROOT.mkdir(parents=True, exist_ok=True)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "sic-core-test-cache",
        "TIMEOUT": 300,
    }
}
