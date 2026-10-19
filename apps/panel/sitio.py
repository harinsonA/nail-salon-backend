from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LogoutView
from django.shortcuts import redirect
from django.urls import path

from apps.panel.forms import PanelAuthenticationForm
from apps.panel.views.inicio.view import InicioPanelView
from apps.tenancy.alta import url_en_dominio


class PanelAdminSite(admin.AdminSite):
    site_header = "Hi Agenda · Panel"
    site_title = "Hi Agenda · Panel"
    login_form = PanelAuthenticationForm

    def each_context(self, request):
        return {**super().each_context(request), "site_url": url_en_dominio(request, settings.DOMINIO_BASE)}

    def get_urls(self):
        from apps.panel.views.users.view import AccountModalView

        account_modal = AccountModalView.as_view(admin_site=self, model_admin=self._registry[get_user_model()])
        return [path("account/modal/", account_modal, name="account_modal"), *super().get_urls()]

    def logout(self, request, extra_context=None):
        request.current_app = self.name
        return LogoutView.as_view(next_page="admin:login")(request)

    def password_change(self, request, extra_context=None):
        return redirect("admin:index")

    def password_change_done(self, request, extra_context=None):
        return redirect("admin:index")

    def index(self, request, extra_context=None):
        request.current_app = self.name
        return InicioPanelView.as_view(admin_site=self)(request)
