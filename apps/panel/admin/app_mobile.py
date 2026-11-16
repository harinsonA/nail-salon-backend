from django.contrib import admin
from django.urls import path

from apps.panel.admin.mixins import DjangoPagesRedirectMixin
from apps.panel.views.app_mobile.view import (
    AppMobileHistoryListAjaxView,
    AppMobileHistoryModalView,
    AppMobileUpdateModalView,
    AppMobileView,
)
from apps.settings.models import PreferenciaPlataforma


@admin.register(PreferenciaPlataforma)
class PreferenciaPlataformaAdmin(DjangoPagesRedirectMixin, admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        change_modal = AppMobileUpdateModalView.as_view(admin_site=self.admin_site, model_admin=self)
        history_modal = AppMobileHistoryModalView.as_view(admin_site=self.admin_site, model_admin=self)
        history_list = AppMobileHistoryListAjaxView.as_view(admin_site=self.admin_site, model_admin=self)
        return [
            path("change/modal/", change_modal, name="settings_preferenciaplataforma_change_modal"),
            path("history/modal/", history_modal, name="settings_preferenciaplataforma_history_modal"),
            path("history/list/", history_list, name="settings_preferenciaplataforma_history_list"),
            *super().get_urls(),
        ]

    def changelist_view(self, request, extra_context=None):
        return AppMobileView.as_view(admin_site=self.admin_site, model_admin=self)(request)
