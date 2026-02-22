"""WSGI config for ece_explainer project."""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ece_explainer.settings')

application = get_wsgi_application()
