from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path

from apps.panel.views.industries.view import (
    IndustryCreateModalView,
    IndustryDeleteModalView,
    IndustryListAjaxView,
    IndustryListView,
    IndustryUpdateModalView,
)
from apps.tenancy.models import Rubro


@admin.register(Rubro)
class RubroAdmin(admin.ModelAdmin):
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

    def add_view(self, request, form_url="", extra_context=None):
        return redirect("admin:tenancy_rubro_changelist")

    def change_view(self, request, object_id, form_url="", extra_context=None):
        return redirect("admin:tenancy_rubro_changelist")

    def delete_view(self, request, object_id, extra_context=None):
        return redirect("admin:tenancy_rubro_changelist")
