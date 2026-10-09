from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django_tenants.utils import get_public_schema_name

from apps.profiles.permisos import SOLO_ADMINISTRACION, administra_el_negocio
from apps.tenancy.models import Negocio
from apps.tenancy.subdominios import SUBDOMINIO_PANEL

NEGOCIO_NO_DISPONIBLE = {
    Negocio.Estado.PREPARANDO: (
        503,
        "Estamos preparando tu agenda",
        "Tu negocio se está configurando. Vuelve a intentarlo en unos minutos.",
    ),
    Negocio.Estado.PAUSADO: (
        410,
        "Servicio suspendido",
        "El acceso a esta agenda está suspendido. Para reactivarlo, comunícate con Hi Agenda.",
    ),
    Negocio.Estado.CANCELADO: (
        410,
        "Servicio finalizado",
        "Esta agenda ya no está disponible. Sus datos se conservan: para recuperarla, comunícate con Hi Agenda.",
    ),
}
PAGO_PENDIENTE = (
    "Hay un pago pendiente con Hi Agenda. La agenda sigue funcionando, pero esta sección "
    "se reactiva cuando se regularice el pago."
)


def es_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


class EstadoDelNegocioMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        negocio = getattr(request, "tenant", None)
        if negocio is None or negocio.schema_name == get_public_schema_name():
            return None
        if negocio.estado in NEGOCIO_NO_DISPONIBLE:
            estado_http, titulo, mensaje = NEGOCIO_NO_DISPONIBLE[negocio.estado]
            if es_ajax(request):
                return JsonResponse({"message": mensaje}, status=estado_http)
            contexto = {"titulo": titulo, "mensaje": mensaje}
            return render(request, "estado/no_disponible.html", contexto, status=estado_http)
        bloqueado = (
            negocio.estado == Negocio.Estado.MOROSO
            and request.resolver_match.url_name in SOLO_ADMINISTRACION
            and administra_el_negocio(request.user)
        )
        if not bloqueado:
            return None
        if es_ajax(request):
            return JsonResponse({"message": PAGO_PENDIENTE}, status=402)
        return render(request, "estado/pago_pendiente.html", {"mensaje": PAGO_PENDIENTE}, status=402)


class PanelSoloEnSubdominioMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if connection.schema_name == get_public_schema_name() and not self.es_el_panel(request):
            request.urlconf = settings.RAIZ_URLCONF
        return self.get_response(request)

    @staticmethod
    def es_el_panel(request):
        return request.get_host().split(":")[0].startswith(f"{SUBDOMINIO_PANEL}.")
