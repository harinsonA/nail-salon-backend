from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.shortcuts import redirect
from django.urls import path

from apps.panel.admin.mixins import DjangoPagesRedirectMixin
from apps.panel.deletion import CurrentSchemaDeletionMixin
from apps.panel.views.users.view import (
    UserCreateModalView,
    UserDeleteModalView,
    UserListAjaxView,
    UserListView,
    UserUnlockModalView,
    UserUpdateModalView,
)

User = get_user_model()

admin.site.unregister(User)


@admin.register(User)
class UserAdmin(DjangoPagesRedirectMixin, CurrentSchemaDeletionMixin, DjangoUserAdmin):
    def get_urls(self):
        list_ajax = UserListAjaxView.as_view(admin_site=self.admin_site, model_admin=self)
        create_modal = UserCreateModalView.as_view(admin_site=self.admin_site, model_admin=self)
        change_modal = UserUpdateModalView.as_view(admin_site=self.admin_site, model_admin=self)
        delete_modal = UserDeleteModalView.as_view(admin_site=self.admin_site, model_admin=self)
        unlock_modal = UserUnlockModalView.as_view(admin_site=self.admin_site, model_admin=self)
        return [
            path("list/", list_ajax, name="auth_user_list_ajax"),
            path("add/modal/", create_modal, name="auth_user_add_modal"),
            path("<int:pk>/change/modal/", change_modal, name="auth_user_change_modal"),
            path("<int:pk>/delete/modal/", delete_modal, name="auth_user_delete_modal"),
            path("<int:pk>/unlock/modal/", unlock_modal, name="auth_user_unlock_modal"),
            *super().get_urls(),
        ]

    def changelist_view(self, request, extra_context=None):
        return UserListView.as_view(admin_site=self.admin_site, model_admin=self)(request)

    def user_change_password(self, request, id, form_url=""):
        return redirect("admin:auth_user_changelist")
