from django.contrib import admin
from django.urls import path

from apps.panel.views.industries.view import IndustryDeleteModalView, IndustryListAjaxView, IndustryListView
from apps.tenancy.models import Rubro


@admin.register(Rubro)
class RubroAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo", "activo", "orden")
    list_editable = ("activo", "orden")
    search_fields = ("nombre", "codigo")

    def get_urls(self):
        list_ajax = IndustryListAjaxView.as_view(admin_site=self.admin_site, model_admin=self)
        delete_modal = IndustryDeleteModalView.as_view(admin_site=self.admin_site, model_admin=self)
        return [
            path("list/", list_ajax, name="tenancy_rubro_list_ajax"),
            path("<int:pk>/delete/modal/", delete_modal, name="tenancy_rubro_delete_modal"),
            *super().get_urls(),
        ]

    def changelist_view(self, request, extra_context=None):
        return IndustryListView.as_view(admin_site=self.admin_site, model_admin=self)(request)
