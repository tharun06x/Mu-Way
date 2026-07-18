"""
Django settings for icrs_backend project.
"""

import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ── Security ──────────────────────────────────────────────────────────────────
# SECURITY WARNING: keep the secret key used in production secret!
_secret_key_raw = os.environ.get('DJANGO_SECRET_KEY', '')
if not _secret_key_raw:
    # Allow insecure default ONLY for local development; fail loudly in production.
    _app_env = os.environ.get('APP_ENV', 'development')
    if _app_env == 'production':
        raise ValueError(
            "DJANGO_SECRET_KEY environment variable must be set in production. "
            "Generate one with: python -c \"from django.core.management.utils import "
            "get_random_secret_key; print(get_random_secret_key())\""
        )
    import warnings
    warnings.warn(
        "DJANGO_SECRET_KEY not set — using insecure development default. "
        "Never use this in production!", stacklevel=1
    )
    _secret_key_raw = 'django-insecure-dev-only-local-key-do-not-use-in-production'

SECRET_KEY = _secret_key_raw

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

# Hosts must be explicitly allowed; '*' is insecure in production.
_allowed_raw = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [h.strip() for h in _allowed_raw.split(',') if h.strip()]


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'icrs.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR.parent / 'frontend' / 'dist'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'icrs.wsgi.application'


# Database
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL', f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
        conn_health_checks=True,
    )
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files
STATIC_URL = 'assets/'
STATICFILES_DIRS = [
    BASE_DIR.parent / 'frontend' / 'dist' / 'assets',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ── CORS ──────────────────────────────────────────────────────────────────────
# Explicit allowlist — never allow all origins in production.
# Set CORS_ALLOWED_ORIGINS in your .env, comma-separated.
_cors_raw = os.environ.get('CORS_ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173')
CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_raw.split(',') if o.strip()]
# Remove the blanket allow-all that was here before (CORS_ALLOW_ALL_ORIGINS = True)

