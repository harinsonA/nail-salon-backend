from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django_tenants.utils import get_public_schema_name

from apps.profiles.models import Perfil

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
