from django.core.exceptions import PermissionDenied
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django_tenants.utils import get_public_schema_name

from apps.profiles.models import Perfil
from apps.profiles.permisos import (
    SOLO_ADMINISTRACION,
    SOLO_CON_EQUIPO,
    administra_el_negocio,
)
from apps.tenancy.user_limit import UserLimit
from apps.tenancy.user_limit.messages import TEAM_DISABLED

RUTAS_PERMITIDAS = {"cambiar_clave", "logout", "session_ping"}


def debe_cambiar_clave(usuario):
    try:
        return usuario.perfil.debe_cambiar_clave
    except Perfil.DoesNotExist:
        return False


class CambioDeClaveObligatorioMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if connection.schema_name == get_public_schema_name():
            return None
        if not request.user.is_authenticated or request.resolver_match.url_name in RUTAS_PERMITIDAS:
            return None
        if not debe_cambiar_clave(request.user):
            return None
        destino = reverse("cambiar_clave")
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"message": "Debes cambiar tu clave temporal.", "redirect": destino}, status=403)
        return redirect(destino)


class PermisosPorRolMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if connection.schema_name == get_public_schema_name() or not request.user.is_authenticated:
            return None
        url_name = request.resolver_match.url_name
        if url_name in SOLO_ADMINISTRACION and not administra_el_negocio(request.user):
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"message": "Esta sección es solo para el propietario y los encargados."}, status=403)
            raise PermissionDenied
        if url_name in SOLO_CON_EQUIPO and not UserLimit.for_request(request).team_enabled:
            destino = reverse("calendar")
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"message": TEAM_DISABLED, "redirect": destino}, status=403)
            return redirect(destino)
        return None
