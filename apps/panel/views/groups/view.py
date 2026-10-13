from django import forms
from django.contrib.auth.models import Group
from django.db.models import Count, Q, TextChoices
from django.urls import reverse
from django.views.generic import TemplateView

from apps.common.form_classes import FORM_SELECT_CLASS
from apps.panel.views.base import PanelListViewAjax, PanelView


class GroupsFilterForm(forms.Form):
    class UsersChoices(TextChoices):
        ALL = "all", "Todos"
        WITH_USERS = "with_users", "Con usuarios"
        WITHOUT_USERS = "without_users", "Sin usuarios"

    users = forms.ChoiceField(
        choices=UsersChoices.choices,
        label="Usuarios",
        initial=UsersChoices.ALL,
        required=False,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )

    def clean(self):
        users = super().clean().get("users")
        if users == self.UsersChoices.WITH_USERS:
            return {"user_count__gt": 0}
        if users == self.UsersChoices.WITHOUT_USERS:
            return {"user_count": 0}
        return {}


class GroupListView(PanelView, TemplateView):
    template_name = "panel/groups/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_add = self.model_admin.has_add_permission(self.request)
        context.update(
            {
                "filter_form": GroupsFilterForm(),
                "list_url": reverse("admin:auth_group_list_ajax", current_app=self.admin_site.name),
                "add_url": reverse("admin:auth_group_add", current_app=self.admin_site.name) if can_add else "",
            }
        )
        return context


class GroupListAjaxView(PanelListViewAjax):
    model = Group
    filter_form_class = GroupsFilterForm
    field_list = ["pk", "name", "permission_count", "user_count"]
    ordering_fields = {
        "0": "name",
        "1": "permission_count",
        "2": "user_count",
    }

    def get_queryset(self):
        return Group.objects.annotate(
            permission_count=Count("permissions", distinct=True),
            user_count=Count("user", distinct=True),
        ).filter(**self.get_filters())

    def get_filter_by_search(self):
        search_value = self.request.GET.get("search[value]", "")
        return Q(name__icontains=search_value) if search_value else Q()

    def add_options_column(self, data):
        can_change = self.model_admin.has_change_permission(self.request)
        can_delete = self.model_admin.has_delete_permission(self.request)
        for item in data:
            options = []
            if can_change:
                options.append(
                    {
                        "label": "Editar",
                        "link": reverse("admin:auth_group_change", args=[item["pk"]]),
                        "icon": "edit_document",
                    }
                )
            if can_delete:
                options.append(
                    {
                        "label": "Eliminar",
                        "link": reverse("admin:auth_group_delete", args=[item["pk"]]),
                        "icon": "delete",
                        "className": "text-color-destructive",
                    }
                )
            item["options"] = options
        return data

    @staticmethod
    def additional_data(queryset):
        return Group.objects.aggregate(
            total_groups=Count("pk", distinct=True),
            groups_with_users=Count("pk", filter=Q(user__isnull=False), distinct=True),
        )
