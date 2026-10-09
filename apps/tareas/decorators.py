from functools import wraps

from celery import shared_task
from django.contrib.auth import get_user_model
from django_tenants.utils import get_public_schema_name, schema_context
from result import Err, Ok

from apps.tareas.models import TareaEnProceso
from apps.tenancy.models import Negocio


def _get_user(user_id):
    """Busca el usuario que disparó la tarea.

    Tolera el id huérfano: como el modelo guarda el id suelto y no una
    ForeignKey, nada garantiza que el usuario siga existiendo.

    Args:
        user_id (int | None): Valor de TareaEnProceso.user_id.

    Returns:
        Result: Ok(User) si existe, o Err(str) con el motivo si la tarea no
            tiene usuario o si ese usuario ya no está.
    """
    if not user_id:
        return Err("La tarea no tiene un usuario asociado.")
    user = get_user_model().objects.filter(pk=user_id).first()
    if not user:
        return Err(f"No existe el usuario con id {user_id} que creó la tarea.")
    return Ok(user)


def tracked_task(func, requires_user=True):
    """Agrega el seguimiento en TareaEnProceso a una función. Pieza interna.

    La función se escribe recibiendo la instancia TareaEnProceso, pero se
    invoca pasando el esquema del negocio y el id (por Redis solo viajan esos
    dos valores). Todo el proceso corre dentro de ese esquema. El usuario se
    busca a partir del user_id de la tarea y se entrega en kwargs["user"].

    Si el esquema no es el de un negocio, la tarea no se ejecuta y se lanza
    ValueError: nunca se lee ni se escribe en otro esquema.

    Si la función lanza cualquier excepción, la tarea queda FALLIDO con el
    detalle en resultado_metadata (nunca EN_PROCESO eterno) y la excepción se
    relanza para que el worker registre el traceback.

    Las tareas del proyecto no usan este decorador directamente: usan
    background_task, que además las registra en Celery.

    Args:
        func (callable): Función a decorar. Recibe (tarea, *args, user=...).
        requires_user (bool): Si es True (default), una tarea sin usuario o
            cuyo usuario ya no existe queda FALLIDO y el proceso no se
            ejecuta. Si es False el proceso corre igual y recibe user=None,
            que es el caso de las tareas periódicas.

    Returns:
        callable: La función envuelta, que se invoca con (esquema, tarea_id, ...).
    """

    @wraps(func)
    def wrapper(esquema, tarea_id, *args, **kwargs):
        _validar_negocio(esquema)
        with schema_context(esquema):
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


def _validar_negocio(esquema):
    publico = get_public_schema_name()
    with schema_context(publico):
        es_negocio = Negocio.objects.filter(schema_name=esquema).exclude(schema_name=publico).exists()
    if not es_negocio:
        raise ValueError(f"«{esquema}» no es el esquema de un negocio: la tarea no se ejecuta.")


def background_task(func=None, *, requires_user=True, **opciones):
    """Decorador público para procesos en segundo plano con seguimiento.

    Equivale a @shared_task + @tracked_task en el orden correcto, para que
    nadie pueda invertirlos por accidente. Es el decorador de los procesos
    RASTREADOS (los que se ven en /procesos/) y presupone una fila
    TareaEnProceso ya creada por quien encola.

    La función decorada debe aceptar el kwarg user: tracked_task lo inyecta
    siempre.

    Example:
        @background_task
        def importar_clientes(tarea, user): ...

        @background_task(max_retries=3)
        def enviar_correos(tarea, user): ...

        @background_task(requires_user=False)
        def enviar_recordatorios(tarea, user): ...

        encolar(importar_clientes, tarea)  # apps.tareas.cola

    Args:
        func (callable, optional): La función, cuando se usa sin paréntesis.
        requires_user (bool): Si es True (default) se garantiza que user es un
            usuario existente; si no lo hay la tarea queda FALLIDO sin
            ejecutar el proceso. False es para los procesos periódicos, que no
            nacen de una persona: ahí user llega como None.
        **opciones: Opciones de shared_task (max_retries, rate_limit...).

    Returns:
        callable: La tarea Celery registrada, o el decorador si se usó con
            paréntesis.

    Raises:
        TypeError: Si se pasa bind=True, que chocaría con el tarea_id
            posicional.
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
