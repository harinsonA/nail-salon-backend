"""
Configuración de Celery para nail_salon_api.

El worker se levanta con:
    celery -A nail_salon_api worker --loglevel=info
(en Windows agregar --pool=solo)
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nail_salon_api.settings")

app = Celery("nail_salon_api")

# Toda la configuración CELERY_* vive en settings.py
app.config_from_object("django.conf:settings", namespace="CELERY")

# Busca tasks.py dentro de cada app instalada (dashboard, apps.clients, etc.)
app.autodiscover_tasks()
