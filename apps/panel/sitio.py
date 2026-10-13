from django.conf import settings
from django.contrib import admin

from apps.tenancy.alta import url_en_dominio


class PanelAdminSite(admin.AdminSite):
    site_header = "Hi Agenda · Panel"
    site_title = "Hi Agenda · Panel"
    index_title = "Negocios y titulares"

    def each_context(self, request):
        return {**super().each_context(request), "site_url": url_en_dominio(request, settings.DOMINIO_BASE)}
