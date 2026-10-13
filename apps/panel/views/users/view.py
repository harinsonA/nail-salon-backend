from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Count, Q, TextChoices, Value
from django.db.models.functions import Concat, Trim
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView
from rest_framework.status import HTTP_400_BAD_REQUEST

from apps.common.form_classes import FORM_SELECT_CLASS
from apps.panel.views.base import PanelDeleteModalView, PanelListViewAjax, PanelView

User = get_user_model()

NEVER = "—"


def format_last_login(value):
    return timezone.localtime(value).strftime("%d/%m/%Y %H:%M") if value else NEVER


class UsersFilterForm(forms.Form):
    class StatusChoices(TextChoices):
        ALL = "all", "Todos"
        ACTIVE = "active", "Activos"
        INACTIVE = "inactive", "Inactivos"

    class RoleChoices(TextChoices):
        ALL = "all", "Todos"
        SUPERUSER = "superuser", "Superusuarios"
        STAFF = "staff", "Staff"
        NO_PANEL = "no_panel", "Sin acceso al panel"

    status = forms.ChoiceField(
        choices=StatusChoices.choices,
        label="Estado",
        initial=StatusChoices.ALL,
        required=False,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    role = forms.ChoiceField(
        choices=RoleChoices.choices,
        label="Rol",
        initial=RoleChoices.ALL,
        required=False,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    group = forms.ModelChoiceField(
        queryset=Group.objects.order_by("name"),
        label="Grupo",
        empty_label="Todos",
        required=False,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )

    def clean(self):
        cleaned_data = super().clean()
        filters = {}
        status = cleaned_data.get("status")
        if status == self.StatusChoices.ACTIVE:
            filters["is_active"] = True
        elif status == self.StatusChoices.INACTIVE:
            filters["is_active"] = False
        role = cleaned_data.get("role")
        if role == self.RoleChoices.SUPERUSER:
            filters["is_superuser"] = True
        elif role == self.RoleChoices.STAFF:
            filters.update(is_staff=True, is_superuser=False)
        elif role == self.RoleChoices.NO_PANEL:
            filters["is_staff"] = False
        if cleaned_data.get("group"):
            filters["groups"] = cleaned_data["group"]
        return filters


class UserListView(PanelView, TemplateView):
    template_name = "panel/users/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_add = self.model_admin.has_add_permission(self.request)
        context.update(
            {
                "filter_form": UsersFilterForm(),
                "list_url": reverse("admin:auth_user_list_ajax", current_app=self.admin_site.name),
                "add_url": reverse("admin:auth_user_add", current_app=self.admin_site.name) if can_add else "",
            }
        )
        return context


class UserListAjaxView(PanelListViewAjax):
    model = User
    filter_form_class = UsersFilterForm
    field_list = ["pk", "username", "full_name", "email", "is_staff", "is_superuser", "is_active", "last_login"]
    ordering_fields = {
        "0": "username",
        "1": "full_name",
        "2": "email",
        "3": "is_staff",
        "4": "is_superuser",
        "5": "is_active",
        "6": "last_login",
    }

    def get_queryset(self):
        return User.objects.annotate(
            full_name=Trim(Concat("first_name", Value(" "), "last_name")),
        ).filter(**self.get_filters())

    def get_filter_by_search(self):
        search_value = self.request.GET.get("search[value]", "")
        if not search_value:
            return Q()
        return (
            Q(username__icontains=search_value)
            | Q(first_name__icontains=search_value)
            | Q(last_name__icontains=search_value)
            | Q(email__icontains=search_value)
        )

    def get_values(self, queryset):
        values = super().get_values(queryset)
        for value in values:
            value["last_login"] = format_last_login(value["last_login"])
        return values

    def add_options_column(self, data):
        can_change = self.model_admin.has_change_permission(self.request)
        can_delete = self.model_admin.has_delete_permission(self.request)
        for item in data:
            options = []
            if can_change:
                options.append(
                    {
                        "label": "Editar",
                        "link": reverse("admin:auth_user_change", args=[item["pk"]]),
                        "icon": "edit_document",
                    }
                )
            if can_delete and item["pk"] != self.request.user.pk:
                options.append(
                    {
                        "label": "Eliminar",
                        "link": reverse("admin:auth_user_delete_modal", args=[item["pk"]]),
                        "bsModal": True,
                        "icon": "delete",
                        "className": "bs-modal text-color-destructive",
                    }
                )
            item["options"] = options
        return data

    @staticmethod
    def additional_data(queryset):
        return User.objects.aggregate(
            total_users=Count("pk"),
            active_users=Count("pk", filter=Q(is_active=True)),
            staff_users=Count("pk", filter=Q(is_staff=True)),
        )


class UserDeleteModalView(PanelDeleteModalView):
    success_message = "Usuario %(name)s eliminado exitosamente."
    own_account_message = "No puedes eliminar tu propia cuenta."

    def get_additional_information(self, user):
        information = []
        if user.email:
            information.append({"text": user.email, "icon": "mail"})
        information.extend(
            [
                {"text": f"Grupos: {user.groups.count()}", "icon": "group"},
                {"text": f"Último acceso: {format_last_login(user.last_login)}", "icon": "schedule"},
            ]
        )
        return information

    def post(self, request, *args, **kwargs):
        if self.get_object().pk == request.user.pk:
            return JsonResponse({"message": self.own_account_message}, status=HTTP_400_BAD_REQUEST)
        return super().post(request, *args, **kwargs)
