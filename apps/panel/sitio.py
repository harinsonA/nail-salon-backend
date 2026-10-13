from django.conf import settings
from django.contrib import admin

from apps.panel.views.inicio.view import InicioPanelView
from apps.tenancy.alta import url_en_dominio


class PanelAdminSite(admin.AdminSite):
    site_header = "Hi Agenda · Panel"
    site_title = "Hi Agenda · Panel"

    def each_context(self, request):
        return {**super().each_context(request), "site_url": url_en_dominio(request, settings.DOMINIO_BASE)}

    def index(self, request, extra_context=None):
        request.current_app = self.name
        return InicioPanelView.as_view(admin_site=self)(request)
