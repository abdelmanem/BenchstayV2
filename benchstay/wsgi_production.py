"""
WSGI config for benchstay project in production environment.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Set the production settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'benchstay.settings_production')

application = get_wsgi_application()