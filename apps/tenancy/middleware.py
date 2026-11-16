from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django_tenants.utils import get_public_schema_name

from apps.common.api_request import ApiRequest
from apps.seguridad.sessions import close_session
from apps.tenancy.business_status import BusinessStatus
from apps.tenancy.business_status.messages import PAYMENT_PENDING
from apps.tenancy.subdominios import SUBDOMINIO_PANEL
from apps.tenancy.user_limit import UserLimit
from apps.tenancy.user_limit.messages import OVER_LIMIT_LOGIN


def es_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


class EstadoDelNegocioMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        status = BusinessStatus.for_request(request)
        if status is None or ApiRequest.matches(request):
            return None
        unavailable = status.unavailable
        if unavailable:
            if es_ajax(request):
                return JsonResponse({"message": unavailable.message}, status=unavailable.status_code)
            contexto = {"titulo": unavailable.title, "mensaje": unavailable.message}
            return render(request, "estado/no_disponible.html", contexto, status=unavailable.status_code)
        if not status.pauses_section(request.resolver_match.url_name, request.user):
            return None
        if es_ajax(request):
            return JsonResponse({"message": PAYMENT_PENDING}, status=BusinessStatus.PAYMENT_PENDING_STATUS)
        return render(
            request,
            "estado/pago_pendiente.html",
            {"mensaje": PAYMENT_PENDING},
            status=BusinessStatus.PAYMENT_PENDING_STATUS,
        )


class UserLimitGuardMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        negocio = getattr(request, "tenant", None)
        user = getattr(request, "user", None)
        if (
            negocio is not None
            and negocio.schema_name != get_public_schema_name()
            and user is not None
            and user.is_authenticated
            and not UserLimit.for_request(request).lets_in(user)
        ):
            close_session(request, OVER_LIMIT_LOGIN)
        return self.get_response(request)


class BusinessTimeZoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        negocio = getattr(request, "tenant", None)
        if negocio is None or negocio.schema_name == get_public_schema_name():
            return self.get_response(request)
        with timezone.override(negocio.zona_horaria):
            return self.get_response(request)


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
