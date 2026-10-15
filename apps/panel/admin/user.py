from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.shortcuts import redirect
from django.urls import path

from apps.panel.deletion import CurrentSchemaDeletionMixin
from apps.panel.views.users.view import UserCreateModalView, UserDeleteModalView, UserListAjaxView, UserListView

User = get_user_model()

admin.site.unregister(User)


@admin.register(User)
class UserAdmin(CurrentSchemaDeletionMixin, DjangoUserAdmin):
    def get_urls(self):
        list_ajax = UserListAjaxView.as_view(admin_site=self.admin_site, model_admin=self)
        create_modal = UserCreateModalView.as_view(admin_site=self.admin_site, model_admin=self)
        delete_modal = UserDeleteModalView.as_view(admin_site=self.admin_site, model_admin=self)
        return [
            path("list/", list_ajax, name="auth_user_list_ajax"),
            path("add/modal/", create_modal, name="auth_user_add_modal"),
            path("<int:pk>/delete/modal/", delete_modal, name="auth_user_delete_modal"),
            *super().get_urls(),
        ]

    def changelist_view(self, request, extra_context=None):
        return UserListView.as_view(admin_site=self.admin_site, model_admin=self)(request)

    def add_view(self, request, form_url="", extra_context=None):
        return redirect("admin:auth_user_changelist")
