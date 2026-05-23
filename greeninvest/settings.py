"""
Green Invest — Django Settings
Projet : Financement vert UEMOA / Données Copernicus Sentinel-2
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-change-this-in-production'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'corsheaders',
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'greeninvest.urls'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ── Copernicus API ──────────────────────────────────────────────
# Remplace par tes vraies clés OAuth Copernicus
COP_CLIENT_ID     = os.environ.get('COP_CLIENT_ID',     'sh-abac5ffd-0091-41b0-8c00-b11e389350dd')
COP_CLIENT_SECRET = os.environ.get('COP_CLIENT_SECRET', 'YTl7Ul12ZpgYOwvPWmwq8knSiMGXdzBc')

# ── CORS : autorise index.html à appeler ce backend ─────────────
CORS_ALLOW_ALL_ORIGINS = True

# ── Cache : le token Copernicus est mis en cache auto ───────────
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

STATIC_URL = '/static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Autoriser les headers personnalisés Copernicus
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'origin',
    'x-cop-id',
    'x-cop-secret',
]
