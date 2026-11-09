from django_tenants.utils import get_public_schema_name

from apps.profiles.permisos import administra_el_negocio
from apps.tenancy.models import Negocio
from apps.tenancy.user_limit import UserLimit


def estado_del_negocio(request):
    negocio = getattr(request, "tenant", None)
    moroso = negocio is not None and negocio.estado == Negocio.Estado.MOROSO
    usuario = getattr(request, "user", None)
    return {"aviso_de_pago": moroso and usuario is not None and administra_el_negocio(usuario)}


def user_limit(request):
    negocio = getattr(request, "tenant", None)
    usuario = getattr(request, "user", None)
    if (
        negocio is None
        or negocio.schema_name == get_public_schema_name()
        or usuario is None
        or not administra_el_negocio(usuario)
    ):
        return {}
    limit = UserLimit.for_request(request)
    return {"team_enabled": limit.team_enabled, "user_limit": limit}
