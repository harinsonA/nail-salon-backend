from functools import wraps

from celery import shared_task
from django.contrib.auth import get_user_model
from result import Err, Ok

from apps.tareas.models import TareaEnProceso


def _get_user(user_id):
    if not user_id:
        return Err("La tarea no tiene un usuario asociado.")
    user = get_user_model().objects.filter(pk=user_id).first()
    if not user:
        return Err(f"No existe el usuario con id {user_id} que creó la tarea.")
    return Ok(user)


def tracked_task(func, requires_user=True):
    """Pieza interna: agrega el seguimiento en TareaEnProceso a una función.

    La función se escribe recibiendo la instancia TareaEnProceso, pero se
    invoca pasando solo el id (por Redis únicamente viaja el id).

    Busca además el usuario a partir del user_id de la tarea y lo entrega en
    kwargs["user"]. Con requires_user=True (default) una tarea sin usuario, o
    cuyo usuario ya no existe, queda FALLIDO y el proceso no se ejecuta. Con
    requires_user=False el proceso corre igual y recibe user=None: es el caso
    de las tareas periódicas, que dispara el reloj y no una persona.

    Si la función lanza cualquier excepción, la tarea queda FALLIDO con
    el detalle en resultado_metadata (nunca EN_PROCESO eterno) y la
    excepción se relanza para que el worker registre el traceback.

    Las tareas del proyecto no usan este decorador directamente:
    usan background_task, que además registra la tarea en Celery.
    """

    @wraps(func)
    def wrapper(tarea_id, *args, **kwargs):
        tarea = TareaEnProceso.objects.get(pk=tarea_id)
        result = _get_user(tarea.user_id)
        if result.is_err() and requires_user:
            tarea.fallar(result.value)
            return None
        kwargs["user"] = result.value if result.is_ok() else None
        try:
            return func(tarea, *args, **kwargs)
        except Exception as exc:
            tarea.fallar(exc)
            raise

    return wrapper


def background_task(func=None, *, requires_user=True, **opciones):
    """Decorador público para procesos en segundo plano con seguimiento.

    Equivale a @shared_task + @tracked_task en el orden correcto, para que
    nadie pueda invertirlos por accidente:

        @background_task
        def importar_clientes(tarea, user): ...

        @background_task(max_retries=3)   # acepta opciones de shared_task
        def enviar_correos(tarea, user): ...

        @background_task(requires_user=False)   # la dispara el reloj
        def enviar_recordatorios(tarea, user): ...

        importar_clientes.delay(tarea.id)

    La función decorada debe aceptar el kwarg user: tracked_task lo inyecta
    siempre. Con requires_user=True (default) se garantiza que es un usuario
    existente, y si no lo hay la tarea queda FALLIDO sin ejecutar el proceso.
    requires_user=False es para los procesos periódicos, que no nacen de una
    persona: ahí user llega como None y la tarea corre igual.

    Alcance: es el decorador de los procesos RASTREADOS (los que se ven en
    la vista de procesos). Presupone una fila TareaEnProceso ya creada por
    quien encola. No soporta bind=True (chocaría con el tarea_id posicional).
    """
    if opciones.get("bind"):
        raise TypeError(
            "background_task no soporta bind=True: la función decorada "
            "recibe la TareaEnProceso como primer argumento, no self."
        )

    def decorador(f):
        return shared_task(**opciones)(tracked_task(f, requires_user=requires_user))

    if func is not None:  # uso sin paréntesis: @background_task
        return decorador(func)
    return decorador  # uso con opciones: @background_task(max_retries=3)
