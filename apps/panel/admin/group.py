from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.models import Group
from django.urls import path

from apps.panel.admin.mixins import DjangoPagesRedirectMixin
from apps.panel.views.groups.view import (
    GroupCreateModalView,
    GroupDeleteModalView,
    GroupListAjaxView,
    GroupListView,
    GroupUpdateModalView,
)

admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(DjangoPagesRedirectMixin, DjangoGroupAdmin):
    def get_urls(self):
        list_ajax = GroupListAjaxView.as_view(admin_site=self.admin_site, model_admin=self)
        create_modal = GroupCreateModalView.as_view(admin_site=self.admin_site, model_admin=self)
        change_modal = GroupUpdateModalView.as_view(admin_site=self.admin_site, model_admin=self)
        delete_modal = GroupDeleteModalView.as_view(admin_site=self.admin_site, model_admin=self)
        return [
            path("list/", list_ajax, name="auth_group_list_ajax"),
            path("add/modal/", create_modal, name="auth_group_add_modal"),
            path("<int:pk>/change/modal/", change_modal, name="auth_group_change_modal"),
            path("<int:pk>/delete/modal/", delete_modal, name="auth_group_delete_modal"),
            *super().get_urls(),
        ]

    def changelist_view(self, request, extra_context=None):
        return GroupListView.as_view(admin_site=self.admin_site, model_admin=self)(request)
