"""
Development-specific Django settings.

Uses SQLite for simplicity, enables debug mode, and relaxes security for local testing.
"""
from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.ngrok.io', '.ngrok-free.app', '.loca.lt', '*']

# SQLite for local development - no PostgreSQL setup required
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Relaxed CORS for local development with ngrok
CORS_ALLOW_ALL_ORIGINS = True

# Show browsable API in development
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
]

# More verbose logging for development
LOGGING['loggers']['apps']['level'] = 'DEBUG'
LOGGING['loggers']['django']['level'] = 'DEBUG'
