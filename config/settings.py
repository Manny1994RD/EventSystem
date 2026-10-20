import os
from pathlib import Path

from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent
# Everything that must survive a container rebuild (database, flyers, backups) lives here.
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEBUG = os.environ.get("DEBUG", "0") == "1"


def _load_secret_key():
    """Use SECRET_KEY from the environment, or create one the first time and keep it in DATA_DIR."""
    from django.core.exceptions import ImproperlyConfigured

    key = os.environ.get("SECRET_KEY", "").strip()
    placeholders = {"change-me", "changeme", "secret", "dev-only-insecure-key-change-me"}
    if key:
        if key.lower() in placeholders or len(key) < 32:
            raise ImproperlyConfigured(
                "SECRET_KEY in .env is a placeholder or too short. Delete that line to have one created "
                "automatically, or paste a long random value."
            )
        return key
    path = DATA_DIR / "secret_key"
    if path.exists():
        return path.read_text().strip()
    import secrets

    key = secrets.token_urlsafe(50)
    path.write_text(key)
    path.chmod(0o600)
    return key


SECRET_KEY = _load_secret_key()

# The address people open, e.g. https://zima.your-tailnet.ts.net. Hosts and trusted origins come from it.
APP_URL = os.environ.get("APP_URL", "").strip().rstrip("/")
_hosts = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()]
_origins = [o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]
if APP_URL:
    from urllib.parse import urlparse

    _hosts.append(urlparse(APP_URL).hostname)
    _origins.append(APP_URL)
ALLOWED_HOSTS = _hosts + ["localhost", "127.0.0.1"]
CSRF_TRUSTED_ORIGINS = _origins

# The low-level Django admin is off unless the tech admin turns it on for a while.
TECH_ADMIN_ENABLED = os.environ.get("TECH_ADMIN_ENABLED", "0") == "1"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "events",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "events.middleware.SettingsCacheMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.setup.FirstRunMiddleware",
    "accounts.middleware.UserLanguageMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "events.context_processors.nav",
                "events.context_processors.brand",
            ],
            "builtins": ["events.templatetags.ui"],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "db.sqlite3",
        # IMMEDIATE makes each change take the write lock up front, so two churches can't both
        # grab the last spot on a day at the same moment.
        "OPTIONS": {"init_command": "PRAGMA journal_mode=WAL;", "transaction_mode": "IMMEDIATE", "timeout": 20},
    }
}

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "events:home"
LOGOUT_REDIRECT_URL = "login"

LANGUAGE_CODE = "es"
LANGUAGES = [("es", _("Spanish")), ("en", _("English"))]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = os.environ.get("TIME_ZONE", "America/Santo_Domingo")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# Flyers are served through a permission-checked view, never directly.
MEDIA_ROOT = DATA_DIR / "media"
MEDIA_URL = "/media/"
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
MAX_FLYER_MB = 15

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if not DEBUG:
    SESSION_COOKIE_SECURE = os.environ.get("SECURE_COOKIES", "1") == "1"
    CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30

# Shared by all app processes, so the login lockout counts every attempt.
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.filebased.FileBasedCache", "LOCATION": DATA_DIR / "cache"}
}
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 15 * 60

BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", DATA_DIR / "backups"))
MAX_FLYER_PREVIEW_PX = 1400
