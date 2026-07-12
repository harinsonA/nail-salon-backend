"""
Tareas de Celery del dashboard.

Por ahora solo contiene una tarea de humo para verificar que la
infraestructura (Redis + worker) está operativa. Las tareas reales
(importaciones, exportaciones, reportes) se agregarán según el plan en
.vscode/propuestas/procesos_segundo_plano/index.html
"""

import time

from celery import shared_task


@shared_task
def tarea_de_prueba(segundos=5):
    """Simula un proceso largo. Verifica el ciclo completo:
    encolar en Redis -> ejecutar en el worker -> guardar resultado.

    Uso desde `python manage.py shell`:
        from dashboard.tasks import tarea_de_prueba
        resultado = tarea_de_prueba.delay(10)
        resultado.id      # id para consultar estado
        resultado.status  # PENDING -> STARTED -> SUCCESS
    """
    time.sleep(segundos)
    return f"Proceso completado después de {segundos} segundos"
