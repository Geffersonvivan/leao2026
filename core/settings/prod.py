from .base import *
from decouple import config
import dj_database_url

DEBUG = False
ALLOWED_HOSTS = ['*']

CSRF_TRUSTED_ORIGINS = ['https://*.up.railway.app']

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
