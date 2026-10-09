from django.conf import settings
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views import defaults
from django_tenants.utils import get_public_schema_name

from apps.tenancy.alta import dominio_de, url_en_dominio
from apps.tenancy.models import Dominio
from apps.tenancy.subdominios import validar_subdominio


def pagina_publica(request):
    negocio = (request.GET.get("negocio") or "").strip().lower()
    error = None
    if negocio:
        destino = url_de_entrada(request, negocio)
        if destino:
            return redirect(destino)
        error = "No encontramos ese negocio. Revisa la dirección que te entregaron."
    contexto = {"negocio": negocio, "error": error, "dominio_base": settings.DOMINIO_BASE}
    return render(request, "publica/inicio.html", contexto)


def url_de_entrada(request, subdominio):
    try:
        validar_subdominio(subdominio)
    except ValidationError:
        return None
    dominio = dominio_de(subdominio)
    existe = Dominio.objects.filter(domain=dominio).exclude(tenant__schema_name=get_public_schema_name()).exists()
    if not existe:
        return None
    return url_en_dominio(request, dominio, "/inicio_sesion/")


def sin_permiso_en_el_panel(request, exception=None):
    return defaults.permission_denied(request, exception, template_name="admin/sin_permiso.html")
