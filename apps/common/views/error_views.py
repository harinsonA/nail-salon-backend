from django.conf import settings
from django.db import connection
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import NoReverseMatch, reverse
from django_tenants.utils import get_public_schema_name

from apps.profiles.permisos import administra_el_negocio
from apps.tenancy.middleware import PanelSoloEnSubdominioMiddleware

"""========================================================================="""
# region ........ Constants

TEMPLATE_NAME = "errores/pagina_de_error.html"
REDIRECT_SECONDS = 10

ERRORS = {
    400: {
        "title": "No pudimos procesar la solicitud",
        "description": "La solicitud llegó incompleta o con datos inválidos. Vuelve {destination} e inténtalo otra vez.",
        "redirect": True,
    },
    403: {
        "title": "No tienes acceso a esta sección",
        "description": "Esta sección es solo para el propietario y los encargados del negocio.",
        "redirect": True,
    },
    404: {
        "title": "Esta página no existe",
        "description": "La dirección que abriste no existe o cambió. Revisa el enlace o vuelve {destination}.",
        "redirect": True,
    },
    500: {
        "title": "Algo falló de nuestro lado",
        "description": "No pudimos completar lo que pediste. El error quedó registrado; intenta de nuevo en unos minutos.",
        "redirect": False,
    },
}

PANEL_FORBIDDEN_DESCRIPTION = "Tu usuario del panel no tiene permiso para esta acción. Pídeselo a un administrador."

# endregion
"""========================================================================="""
# region ........ Helpers


def safe_reverse(name, urlconf):
    try:
        return reverse(name, urlconf=urlconf)
    except NoReverseMatch:
        return "/"


def business_home(request):
    try:
        manages = administra_el_negocio(request.user)
    except Exception:
        manages = False
    if manages:
        return safe_reverse("dashboard", settings.ROOT_URLCONF), "Ir al dashboard", "al dashboard"
    return safe_reverse("calendar", settings.ROOT_URLCONF), "Ir al calendario", "al calendario"


def site_context(request):
    if connection.schema_name != get_public_schema_name():
        url, label, destination = business_home(request)
        name = getattr(connection.tenant, "nombre", "")
        footer = f"Hi Agenda · {name}" if name else "Hi Agenda"
        return {"site": "negocio", "home_url": url, "home_label": label, "destination": destination, "footer": footer}
    if PanelSoloEnSubdominioMiddleware.es_el_panel(request):
        return {
            "site": "panel",
            "home_url": safe_reverse("admin:index", settings.PUBLIC_SCHEMA_URLCONF),
            "home_label": "Ir al inicio del panel",
            "destination": "al inicio del panel",
            "footer": "Hi Agenda · Panel de administración",
        }
    return {
        "site": "raiz",
        "home_url": safe_reverse("pagina_publica", settings.RAIZ_URLCONF),
        "home_label": "Ir al inicio",
        "destination": "al inicio",
        "footer": "Hi Agenda",
    }


def error_response(request, status):
    error = ERRORS[status]
    context = site_context(request)
    description = error["description"]
    if status == 403 and context["site"] == "panel":
        description = PANEL_FORBIDDEN_DESCRIPTION
    context.update(
        status=status,
        title=error["title"],
        description=description.format(destination=context["destination"]),
        redirect=error["redirect"],
        redirect_seconds=REDIRECT_SECONDS,
    )
    return HttpResponse(render_to_string(TEMPLATE_NAME, context), status=status)


# endregion
"""========================================================================="""
# region ........ Views


def bad_request(request, exception=None):
    return error_response(request, 400)


def permission_denied(request, exception=None):
    return error_response(request, 403)


def page_not_found(request, exception=None):
    return error_response(request, 404)


def server_error(request):
    return error_response(request, 500)


# endregion
"""========================================================================="""
