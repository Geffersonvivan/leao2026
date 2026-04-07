from .base import *
from decouple import config
import dj_database_url

DEBUG = False
ALLOWED_HOSTS = ['www.leao2026.com.br', 'leao2026.com.br', '*.up.railway.app']

CSRF_TRUSTED_ORIGINS = ['https://*.up.railway.app', 'https://www.leao2026.com.br', 'https://leao2026.com.br']

DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default='postgres://localhost'),
        conn_max_age=600
    )
}

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
