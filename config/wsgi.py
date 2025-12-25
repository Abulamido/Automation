"""
WSGI config for WhatsApp Orders project.

Exposes the WSGI callable as a module-level variable named ``application``.
Used by production WSGI servers like Gunicorn.
"""
import os

from django.core.wsgi import get_wsgi_application

# Default to production in WSGI context
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

application = get_wsgi_application()
