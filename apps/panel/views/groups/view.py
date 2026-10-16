import re

from bootstrap_modal_forms.forms import BSModalForm
from django import forms
from django.contrib.auth.models import Group, Permission
from django.db.models import Count, Q, TextChoices
from django.urls import reverse
from django.views.generic import TemplateView

from apps.common.form_classes import FORM_CONTROL_CLASS, FORM_SELECT_CLASS
from apps.panel.permissions import (
    build_permission_rows,
    merge_panel_permissions,
    panel_permission_ids,
    panel_permissions,
    permission_action_labels,
)
from apps.panel.views.base import (
    PanelCreateModalView,
    PanelDeleteModalView,
    PanelListViewAjax,
    PanelUpdateModalView,
    PanelView,
)

"""========================================================================="""
# region ........ Constants


GROUP_NAME_MIN_LENGTH = 3
GROUP_NAME_MAX_LENGTH = 80
GROUP_NAME_PATTERN = re.compile(r"^[^\W_][\w .-]*$")


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Forms


class GroupForm(BSModalForm):
    name = forms.CharField(
        label="Nombre",
        help_text="Entre 3 y 80 caracteres: letras, números, espacios, punto, guion y guion bajo.",
        widget=forms.TextInput(
            attrs={"class": FORM_CONTROL_CLASS, "placeholder": "Soporte", "maxlength": GROUP_NAME_MAX_LENGTH}
        ),
    )
    permissions = forms.ModelMultipleChoiceField(
        label="Permisos",
        queryset=Permission.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        super().__init__(*args, **kwargs)
        self.fields["permissions"].queryset = panel_permissions()
        if instance is not None:
            self.initial.update(
                {
                    "name": instance.name,
                    "permissions": list(
                        instance.permissions.filter(pk__in=panel_permission_ids()).values_list("pk", flat=True)
                    ),
                }
            )

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())
        if not GROUP_NAME_MIN_LENGTH <= len(name) <= GROUP_NAME_MAX_LENGTH:
            raise forms.ValidationError(
                f"El nombre debe tener entre {GROUP_NAME_MIN_LENGTH} y {GROUP_NAME_MAX_LENGTH} caracteres."
            )
        if not GROUP_NAME_PATTERN.match(name):
            raise forms.ValidationError(
                "El nombre solo admite letras, números, espacios, punto, guion y guion bajo, y debe empezar "
                "con una letra o un número."
            )
        groups = Group.objects.exclude(pk=self.instance.pk) if self.instance else Group.objects.all()
        if groups.filter(name__iexact=name).exists():
            raise forms.ValidationError("Ya existe un grupo con ese nombre.")
        return name

    def save(self):
        group = self.instance or Group()
        group.name = self.cleaned_data["name"]
        group.save()
        current = set(group.permissions.values_list("pk", flat=True))
        selected = {permission.pk for permission in self.cleaned_data["permissions"]}
        group.permissions.set(merge_panel_permissions(current, selected))
        return group


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


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Mixins


class GroupModalMixin:
    template_name = "panel/groups/group_modal.html"
    form_class = GroupForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = context.get("object")
        direct = set(context["form"].initial.get("permissions", []))
        context.update(
            {
                "permission_actions": permission_action_labels(),
                "permission_rows": build_permission_rows(direct),
                "user_count": group.user_set.count() if group else 0,
            }
        )
        return context


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class GroupListView(PanelView, TemplateView):
    template_name = "panel/groups/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_add = self.model_admin.has_add_permission(self.request)
        context.update(
            {
                "filter_form": GroupsFilterForm(),
                "list_url": reverse("admin:auth_group_list_ajax", current_app=self.admin_site.name),
                "create_modal_url": (
                    reverse("admin:auth_group_add_modal", current_app=self.admin_site.name) if can_add else ""
                ),
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
                        "link": reverse("admin:auth_group_change_modal", args=[item["pk"]]),
                        "bsModal": True,
                        "icon": "edit_document",
                        "className": "bs-xl-modal",
                    }
                )
            if can_delete:
                options.append(
                    {
                        "label": "Eliminar",
                        "link": reverse("admin:auth_group_delete_modal", args=[item["pk"]]),
                        "bsModal": True,
                        "icon": "delete",
                        "className": "bs-modal text-color-destructive",
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


class GroupCreateModalView(GroupModalMixin, PanelCreateModalView):
    success_message = "Grupo %(name)s creado exitosamente."

    def create_object(self, form):
        return form.save()


class GroupUpdateModalView(GroupModalMixin, PanelUpdateModalView):
    success_message = "Grupo %(name)s actualizado exitosamente."

    def update_object(self, form):
        return form.save()


class GroupDeleteModalView(PanelDeleteModalView):
    success_message = "Grupo %(name)s eliminado exitosamente."

    def get_additional_information(self, group):
        return [
            {"text": f"Permisos: {group.permissions.count()}", "icon": "key"},
            {"text": f"Usuarios asignados: {group.user_set.count()}", "icon": "group"},
        ]


# endregion
"""========================================================================="""
