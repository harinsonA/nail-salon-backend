from functools import wraps

from celery import shared_task

from apps.tareas.models import TareaEnProceso


def tracked_task(func):
    """Pieza interna: agrega el seguimiento en TareaEnProceso a una función.

    La función se escribe recibiendo la instancia TareaEnProceso, pero se
    invoca pasando solo el id (por Redis únicamente viaja el id).

    Si la función lanza cualquier excepción, la tarea queda FALLIDO con
    el detalle en resultado_metadata (nunca EN_PROCESO eterno) y la
    excepción se relanza para que el worker registre el traceback.

    Las tareas del proyecto no usan este decorador directamente:
    usan background_task, que además registra la tarea en Celery.
    """

    @wraps(func)
    def wrapper(tarea_id, *args, **kwargs):
        tarea = TareaEnProceso.objects.get(pk=tarea_id)
        try:
            return func(tarea, *args, **kwargs)
        except Exception as exc:
            tarea.fallar(exc)
            raise

    return wrapper


def background_task(func=None, **opciones):
    """Decorador público para procesos en segundo plano con seguimiento.

    Equivale a @shared_task + @tracked_task en el orden correcto, para que
    nadie pueda invertirlos por accidente:

        @background_task
        def importar_clientes(tarea): ...

        @background_task(max_retries=3)   # acepta opciones de shared_task
        def enviar_correos(tarea): ...

        importar_clientes.delay(tarea.id)

    Alcance: es el decorador de los procesos RASTREADOS (los que se ven en
    la vista de procesos). Presupone una fila TareaEnProceso ya creada por
    la vista. Las tareas de celery beat (sin fila previa) usan @shared_task
    directo. No soporta bind=True (chocaría con el tarea_id posicional).
    """
    if opciones.get("bind"):
        raise TypeError(
            "background_task no soporta bind=True: la función decorada "
            "recibe la TareaEnProceso como primer argumento, no self."
        )

    def decorador(f):
        return shared_task(**opciones)(tracked_task(f))

    if func is not None:  # uso sin paréntesis: @background_task
        return decorador(func)
    return decorador  # uso con opciones: @background_task(max_retries=3)
