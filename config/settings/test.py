from .base import *  # noqa: F401, F403
from .base import env

SECRET_KEY = "test-secret-key-not-for-production"  # noqa: S105

DEBUG = False

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://postgres:postgres@localhost:5432/__PROJECT_SLUG___test",
    ),
}

# Speed up password hashing in tests
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
