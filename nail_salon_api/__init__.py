# Garantiza que Celery se cargue junto con Django para que
# los decoradores @shared_task queden vinculados a esta app.
from .celery import app as celery_app

__all__ = ("celery_app",)
