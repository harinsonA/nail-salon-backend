from django.core.exceptions import ValidationError

from apps.tenancy.models import Negocio

Estado = Negocio.Estado

TRANSICIONES = {
    Estado.PREPARANDO: set(),
    Estado.ACTIVO: {Estado.MOROSO, Estado.PAUSADO, Estado.CANCELADO},
    Estado.MOROSO: {Estado.ACTIVO, Estado.PAUSADO, Estado.CANCELADO},
    Estado.PAUSADO: {Estado.ACTIVO, Estado.CANCELADO},
    Estado.CANCELADO: {Estado.ACTIVO},
}


def estados_posibles(negocio):
    return [estado for estado in Estado if estado in TRANSICIONES[negocio.estado]]


def cambiar_estado(negocio, nuevo, motivo, usuario=None):
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError("Escribe el motivo del cambio: queda en el historial del negocio.")
    if nuevo not in TRANSICIONES[negocio.estado]:
        raise ValidationError(
            "Un negocio «%(actual)s» no puede pasar a «%(nuevo)s».",
            params={"actual": negocio.get_estado_display(), "nuevo": Estado(nuevo).label},
        )
    negocio.estado = nuevo
    negocio._change_reason = motivo
    if usuario is not None:
        negocio._history_user = usuario
    negocio.save()
    return negocio
