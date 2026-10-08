from django.conf import settings
from django.db import connection
from django_tenants.utils import get_public_schema_name

from apps.tenancy.subdominios import SUBDOMINIO_PANEL


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
