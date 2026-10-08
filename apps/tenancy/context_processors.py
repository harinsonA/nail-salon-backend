from apps.profiles.permisos import administra_el_negocio
from apps.tenancy.models import Negocio


def estado_del_negocio(request):
    negocio = getattr(request, "tenant", None)
    moroso = negocio is not None and negocio.estado == Negocio.Estado.MOROSO
    usuario = getattr(request, "user", None)
    return {"aviso_de_pago": moroso and usuario is not None and administra_el_negocio(usuario)}
