from datetime import timedelta
from pathlib import Path

import environ

from config.logging import configure_logging
from config.otel import setup_otel

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, []),
    JWT_ACCESS_TOKEN_LIFETIME_HOURS=(int, 1),
    JWT_REFRESH_TOKEN_LIFETIME_DAYS=(int, 7),
    LOG_LEVEL=(str, "INFO"),
    OTEL_ENABLED=(bool, False),
    REDIS_URL=(str, ""),
    REQUEST_LOG_ENABLED=(bool, True),
    SLOW_REQUEST_THRESHOLD_MS=(int, 1000),
    REQUEST_LOG_SKIP_PATHS=(list, ["/healthz", "/readyz"]),
    DB_CONN_MAX_AGE=(int, 60),
    DB_CONN_HEALTH_CHECKS=(bool, True),
    DB_CONNECT_TIMEOUT=(int, 5),
    ACCOUNT_CHART_CACHE_TIMEOUT=(int, 300),
    ACCOUNT_VISIBILITY_CACHE_TIMEOUT=(int, 300),
    REGISTRATION_CONFIG_CACHE_TIMEOUT=(int, 300),
    TENANT_ALLOWED_IDS=(list, []),
    ENABLE_ADMIN_SITE=(bool, True),
    ENABLE_API_DOCS=(bool, True),
    ENABLE_EXAMPLE_API=(bool, True),
    AUTH_REGISTER_THROTTLE_RATE=(str, "6/min"),
    AUTH_TOKEN_OBTAIN_THROTTLE_RATE=(str, "12/min"),
    AUTH_TOKEN_REFRESH_THROTTLE_RATE=(str, "30/min"),
)

environ.Env.read_env(BASE_DIR / ".env", overwrite=False)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="unsafe-default-do-not-use-in-production")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "django_filters",
    "mptt",
    "hordak",
    "apps.users",
    "apps.courses",
    "apps.companies",
    "apps.accounts",
    "apps.journal",
    "apps.reports",
    "apps.example",
]

AUTH_USER_MODEL = "users.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "config.middleware.request_id.RequestIDMiddleware",
    "config.middleware.tenant.TenantMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "config.middleware.request_logging.RequestLoggingMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL", default="sqlite:///db.sqlite3"),
}
DATABASES["default"]["CONN_MAX_AGE"] = env("DB_CONN_MAX_AGE")
DATABASES["default"]["CONN_HEALTH_CHECKS"] = env("DB_CONN_HEALTH_CHECKS")

if DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql":
    db_options = DATABASES["default"].setdefault("OPTIONS", {})
    db_options.setdefault("connect_timeout", env("DB_CONNECT_TIMEOUT"))

REDIS_URL = env("REDIS_URL")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": "sic_core",
            "TIMEOUT": 300,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "sic-core-local-cache",
            "TIMEOUT": 300,
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "origin",
    "x-csrftoken",
    "x-requested-with",
    "x-request-id",
]

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "config.exceptions.api_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "auth_register": env("AUTH_REGISTER_THROTTLE_RATE"),
        "auth_token_obtain": env("AUTH_TOKEN_OBTAIN_THROTTLE_RATE"),
        "auth_token_refresh": env("AUTH_TOKEN_REFRESH_THROTTLE_RATE"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=env("JWT_ACCESS_TOKEN_LIFETIME_HOURS")),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env("JWT_REFRESH_TOKEN_LIFETIME_DAYS")),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SIC API",
    "DESCRIPTION": "Implementation of accounting system based in hordak and following SIC (Andrisani) definitions.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "CONTACT": {"name": "gastong256"},
    "SCHEMA_PATH_PREFIX": "/api/v[0-9]",
}

LOG_LEVEL = env("LOG_LEVEL")
JSON_LOGS = env.bool("JSON_LOGS", default=True)
REQUEST_LOG_ENABLED = env("REQUEST_LOG_ENABLED")
SLOW_REQUEST_THRESHOLD_MS = env("SLOW_REQUEST_THRESHOLD_MS")
REQUEST_LOG_SKIP_PATHS = env("REQUEST_LOG_SKIP_PATHS")
ACCOUNT_CHART_CACHE_TIMEOUT = env("ACCOUNT_CHART_CACHE_TIMEOUT")
ACCOUNT_VISIBILITY_CACHE_TIMEOUT = env("ACCOUNT_VISIBILITY_CACHE_TIMEOUT")
REGISTRATION_CONFIG_CACHE_TIMEOUT = env("REGISTRATION_CONFIG_CACHE_TIMEOUT")
TENANT_ALLOWED_IDS = env("TENANT_ALLOWED_IDS")
ENABLE_ADMIN_SITE = env("ENABLE_ADMIN_SITE")
ENABLE_API_DOCS = env("ENABLE_API_DOCS")
ENABLE_EXAMPLE_API = env("ENABLE_EXAMPLE_API")
configure_logging(log_level=LOG_LEVEL, json_logs=JSON_LOGS)

setup_otel()
