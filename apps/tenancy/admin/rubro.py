from django.contrib import admin
from django.urls import path

from apps.panel.admin.mixins import DjangoPagesRedirectMixin
from apps.panel.views.industries.view import (
    IndustryCreateModalView,
    IndustryDeleteModalView,
    IndustryListAjaxView,
    IndustryListView,
    IndustryUpdateModalView,
)
from apps.tenancy.models import Rubro


@admin.register(Rubro)
class RubroAdmin(DjangoPagesRedirectMixin, admin.ModelAdmin):
    list_display = ("nombre", "codigo", "activo")
    list_editable = ("activo",)
    search_fields = ("nombre", "codigo")

    def get_urls(self):
        list_ajax = IndustryListAjaxView.as_view(admin_site=self.admin_site, model_admin=self)
        create_modal = IndustryCreateModalView.as_view(admin_site=self.admin_site, model_admin=self)
        change_modal = IndustryUpdateModalView.as_view(admin_site=self.admin_site, model_admin=self)
        delete_modal = IndustryDeleteModalView.as_view(admin_site=self.admin_site, model_admin=self)
        return [
            path("list/", list_ajax, name="tenancy_rubro_list_ajax"),
            path("add/modal/", create_modal, name="tenancy_rubro_add_modal"),
            path("<int:pk>/change/modal/", change_modal, name="tenancy_rubro_change_modal"),
            path("<int:pk>/delete/modal/", delete_modal, name="tenancy_rubro_delete_modal"),
            *super().get_urls(),
        ]

    def changelist_view(self, request, extra_context=None):
        return IndustryListView.as_view(admin_site=self.admin_site, model_admin=self)(request)
