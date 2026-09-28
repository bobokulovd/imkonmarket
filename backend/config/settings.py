import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BASE_DIR.parent


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    return str(env(key, default)).lower() in ("1", "true", "yes", "on")


SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-change-me-9c1f0f3e5b-7a2d4e6f8a0c2e4f")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS", "*").split(",")
CSRF_TRUSTED_ORIGINS = [o for o in env("CSRF_TRUSTED_ORIGINS", "").split(",") if o]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "corsheaders",
    "market",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
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
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"

if env("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB"),
            "USER": env("POSTGRES_USER", "postgres"),
            "PASSWORD": env("POSTGRES_PASSWORD", ""),
            "HOST": env("POSTGRES_HOST", "localhost"),
            "PORT": env("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "uz"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

CORS_ALLOW_ALL_ORIGINS = env_bool("CORS_ALLOW_ALL", True)
CORS_ALLOWED_ORIGINS = [o for o in env("CORS_ALLOWED_ORIGINS", "").split(",") if o]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "market.pagination.Pagination",
    "PAGE_SIZE": 24,
}
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=12),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
}

# --- Platforma sozlamalari ---
BRAND_NAME = env("BRAND_NAME", "ImkonMarket")
SITE_URL = env("SITE_URL", "http://localhost:3000")  # sayt manzili (shartnomadagi QR, to'lov qaytish)
API_URL = env("API_URL", "http://localhost:8000")
# Rasm/PDF havolalari uchun tashqi manzil (masalan https://imkonmarket.uz). Bo'sh bo'lsa — so'rov hostidan.
PUBLIC_URL = env("PUBLIC_URL", "")

# Reverse-proxy (Traefik / Next.js rewrite) ortida
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# To'lov tizimlari. Kalitlar bo'lmasa — DEMO rejim (sayt/ilovada "Demo" belgisi bilan).
PAYME_MERCHANT_ID = env("PAYME_MERCHANT_ID", "")
PAYME_KEY = env("PAYME_KEY", "")
PAYME_TEST = env_bool("PAYME_TEST", True)
CLICK_SERVICE_ID = env("CLICK_SERVICE_ID", "")
CLICK_MERCHANT_ID = env("CLICK_MERCHANT_ID", "")
CLICK_SECRET_KEY = env("CLICK_SECRET_KEY", "")
CLICK_MERCHANT_USER_ID = env("CLICK_MERCHANT_USER_ID", "")
