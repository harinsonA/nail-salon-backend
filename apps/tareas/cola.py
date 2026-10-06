from django.db import connection
from django_tenants.utils import get_public_schema_name


def encolar(tarea_celery, tarea, *args, **kwargs):
    esquema = connection.schema_name
    if esquema == get_public_schema_name():
        raise RuntimeError("Los procesos con seguimiento solo se encolan desde dentro de un negocio.")
    resultado = tarea_celery.delay(esquema, tarea.id, *args, **kwargs)
    tarea.celery_task_id = resultado.id
    tarea.save(update_fields=["celery_task_id", "modified"])
    return resultado
