from django import forms
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.models import Group, Permission
from django.db.models import Count, Q, TextChoices, Value
from django.db.models.functions import Concat, Trim
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView
from bootstrap_modal_forms.forms import BSModalForm
from rest_framework.status import HTTP_400_BAD_REQUEST

from apps.common.form_classes import FORM_CONTROL_CLASS, FORM_SELECT2_CLASS, FORM_SELECT_CLASS
from apps.common.utils.passwords import PasswordPolicyValidator
from apps.common.utils.utils import USERNAME_MAX_LENGTH, CommonCleaner
from apps.panel.permissions import (
    build_permission_rows,
    group_permission_map,
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


User = get_user_model()

NEVER = "—"
NAME_PART_MAX_LENGTH = 50
DATETIME_FORMAT = "%d/%m/%Y %H:%M"



# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Helpers


def format_datetime(value):
    return timezone.localtime(value).strftime(DATETIME_FORMAT) if value else NEVER


def format_last_login(value):
    return format_datetime(value)


def join_name_parts(*parts):
    return " ".join(part for part in parts if part)


def split_name(full_name):
    first, _, rest = (full_name or "").strip().partition(" ")
    return first, rest.strip()


def text_input(placeholder="", **attrs):
    return forms.TextInput(attrs={"class": FORM_CONTROL_CLASS, "placeholder": placeholder, **attrs})


def password_input():
    return forms.PasswordInput(attrs={"class": FORM_CONTROL_CLASS, "autocomplete": "new-password"})


def switch_input():
    return forms.CheckboxInput(attrs={"class": "form-check-input", "role": "switch"})


def user_permission_rows(user):
    direct = set(user.user_permissions.values_list("pk", flat=True))
    inherited = set(Permission.objects.filter(group__user=user).values_list("pk", flat=True))
    return build_permission_rows(direct, inherited)


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Forms


class UserFormBase(BSModalForm):
    username = forms.CharField(
        label="Usuario",
        help_text="Entre 3 y 30 caracteres: minúsculas, números, punto, guion y guion bajo.",
        widget=text_input(
            "ana.rojas", maxlength=USERNAME_MAX_LENGTH, autocapitalize="none", autocomplete="off", spellcheck="false"
        ),
    )
    first_name = forms.CharField(label="Primer nombre", max_length=NAME_PART_MAX_LENGTH, widget=text_input("Ana"))
    second_name = forms.CharField(
        label="Segundo nombre", max_length=NAME_PART_MAX_LENGTH, required=False, widget=text_input("María")
    )
    first_surname = forms.CharField(
        label="Primer apellido", max_length=NAME_PART_MAX_LENGTH, widget=text_input("Rojas")
    )
    second_surname = forms.CharField(
        label="Segundo apellido", max_length=NAME_PART_MAX_LENGTH, required=False, widget=text_input("Pérez")
    )
    email = forms.EmailField(
        label="Correo",
        max_length=254,
        widget=forms.EmailInput(attrs={"class": FORM_CONTROL_CLASS, "placeholder": "ana.rojas@hiagenda.cl"}),
    )
    is_active = forms.BooleanField(label="Activo", required=False, initial=True, widget=switch_input())
    is_staff = forms.BooleanField(label="Acceso al panel", required=False, initial=True, widget=switch_input())
    is_superuser = forms.BooleanField(label="Superusuario", required=False, initial=False, widget=switch_input())

    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        super().__init__(*args, **kwargs)

    def other_users(self):
        users = User.objects.all()
        return users.exclude(pk=self.instance.pk) if self.instance else users

    def clean_username(self):
        result = CommonCleaner.clean_username_field(self.cleaned_data["username"])
        if result.is_err():
            raise forms.ValidationError(result.value)
        if self.other_users().filter(username__iexact=result.value).exists():
            raise forms.ValidationError("Ese usuario ya existe en el panel.")
        return result.value

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if self.other_users().filter(email__iexact=email).exists():
            raise forms.ValidationError("Ese correo ya lo usa otro usuario del panel.")
        return email

    def clean_name_part(self, field_name):
        value = " ".join(self.cleaned_data.get(field_name, "").split())
        if not value:
            return ""
        result = CommonCleaner.clean_alphabetic_field(self.fields[field_name].label.lower(), value)
        if result.is_err():
            raise forms.ValidationError(result.value)
        return result.value

    def clean_first_name(self):
        return self.clean_name_part("first_name")

    def clean_second_name(self):
        return self.clean_name_part("second_name")

    def clean_first_surname(self):
        return self.clean_name_part("first_surname")

    def clean_second_surname(self):
        return self.clean_name_part("second_surname")

    def clean_password_pair(self, cleaned_data):
        password = cleaned_data.get("password")
        confirmation = cleaned_data.get("password_confirmation")
        if password and confirmation and password != confirmation:
            self.add_error("password_confirmation", "Las contraseñas no coinciden.")
            return
        if not password:
            return
        candidate = User(
            username=cleaned_data.get("username", ""),
            email=cleaned_data.get("email", ""),
            first_name=self.full_first_name(),
            last_name=self.full_last_name(),
        )
        result = CommonCleaner.clean_password_field(password, user=candidate)
        if result.is_err():
            self.add_error("password", result.value)

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("is_superuser"):
            cleaned_data["is_staff"] = True
        return cleaned_data

    def full_first_name(self):
        return join_name_parts(self.cleaned_data.get("first_name"), self.cleaned_data.get("second_name"))

    def full_last_name(self):
        return join_name_parts(self.cleaned_data.get("first_surname"), self.cleaned_data.get("second_surname"))


class UserCreateForm(UserFormBase):
    password = forms.CharField(
        label="Contraseña",
        strip=False,
        help_text=PasswordPolicyValidator().get_help_text(),
        widget=password_input(),
    )
    password_confirmation = forms.CharField(label="Repetir contraseña", strip=False, widget=password_input())

    def clean(self):
        cleaned_data = super().clean()
        self.clean_password_pair(cleaned_data)
        return cleaned_data

    def user_data(self):
        return {
            "username": self.cleaned_data["username"],
            "email": self.cleaned_data["email"],
            "password": self.cleaned_data["password"],
            "first_name": self.full_first_name(),
            "last_name": self.full_last_name(),
            "is_active": self.cleaned_data["is_active"],
            "is_staff": self.cleaned_data["is_staff"],
            "is_superuser": self.cleaned_data["is_superuser"],
        }


class UserUpdateForm(UserFormBase):
    password = forms.CharField(
        label="Nueva contraseña",
        strip=False,
        required=False,
        help_text=PasswordPolicyValidator().get_help_text(),
        widget=password_input(),
    )
    password_confirmation = forms.CharField(
        label="Repetir nueva contraseña", strip=False, required=False, widget=password_input()
    )
    groups = forms.ModelMultipleChoiceField(
        label="Grupos",
        queryset=Group.objects.order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": FORM_SELECT2_CLASS}),
    )
    user_permissions = forms.ModelMultipleChoiceField(
        label="Permisos individuales",
        queryset=Permission.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, instance=instance, **kwargs)
        self.fields["user_permissions"].queryset = panel_permissions()
        first_name, second_name = split_name(instance.first_name)
        first_surname, second_surname = split_name(instance.last_name)
        self.initial.update(
            {
                "username": instance.username,
                "first_name": first_name,
                "second_name": second_name,
                "first_surname": first_surname,
                "second_surname": second_surname,
                "email": instance.email,
                "is_active": instance.is_active,
                "is_staff": instance.is_staff,
                "is_superuser": instance.is_superuser,
                "groups": list(instance.groups.values_list("pk", flat=True)),
                "user_permissions": list(
                    instance.user_permissions.filter(pk__in=self.fields["user_permissions"].queryset)
                    .values_list("pk", flat=True)
                ),
            }
        )
        editor = getattr(self.request, "user", None)
        if self.is_own_account():
            for field_name in ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"):
                self.fields[field_name].disabled = True
        elif editor is None or not editor.is_superuser:
            self.fields["is_superuser"].disabled = True

    def is_own_account(self):
        editor = getattr(self.request, "user", None)
        return editor is not None and editor.pk == self.instance.pk

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirmation = cleaned_data.get("password_confirmation")
        if confirmation and not password:
            self.add_error("password", "Escribe la nueva contraseña.")
        elif password and not confirmation:
            self.add_error("password_confirmation", "Repite la nueva contraseña.")
        else:
            self.clean_password_pair(cleaned_data)
        return cleaned_data

    def save(self):
        user = self.instance
        data = self.cleaned_data
        user.username = data["username"]
        user.email = data["email"]
        user.first_name = self.full_first_name()
        user.last_name = self.full_last_name()
        user.is_active = data["is_active"]
        user.is_staff = data["is_staff"]
        user.is_superuser = data["is_superuser"]
        if data.get("password"):
            user.set_password(data["password"])
        user.save()
        if not self.fields["groups"].disabled:
            user.groups.set(data["groups"])
        if not self.fields["user_permissions"].disabled:
            self.save_permissions(user, data["groups"], data["user_permissions"])
        return user

    @staticmethod
    def save_permissions(user, groups, selected):
        current = set(user.user_permissions.values_list("pk", flat=True))
        inherited = set(
            Permission.objects.filter(group__in=groups, pk__in=panel_permission_ids()).values_list("pk", flat=True)
        )
        user.user_permissions.set(merge_panel_permissions(current, {permission.pk for permission in selected}, inherited))


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


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class UserListView(PanelView, TemplateView):
    template_name = "panel/users/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_add = self.model_admin.has_add_permission(self.request)
        context.update(
            {
                "filter_form": UsersFilterForm(),
                "list_url": reverse("admin:auth_user_list_ajax", current_app=self.admin_site.name),
                "create_modal_url": (
                    reverse("admin:auth_user_add_modal", current_app=self.admin_site.name) if can_add else ""
                ),
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
        editor_is_superuser = self.request.user.is_superuser
        for item in data:
            options = []
            if can_change and (editor_is_superuser or not item["is_superuser"]):
                options.append(
                    {
                        "label": "Editar",
                        "link": reverse("admin:auth_user_change_modal", args=[item["pk"]]),
                        "bsModal": True,
                        "icon": "edit_document",
                        "className": "bs-xl-modal",
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


class UserCreateModalView(PanelCreateModalView):
    template_name = "panel/users/user_modal.html"
    form_class = UserCreateForm
    success_message = "Usuario %(name)s creado exitosamente."

    def create_object(self, form):
        return User.objects.create_user(**form.user_data())


class UserUpdateModalView(PanelUpdateModalView):
    template_name = "panel/users/user_edit_modal.html"
    form_class = UserUpdateForm
    success_message = "Usuario %(name)s actualizado exitosamente."

    def has_model_permission(self, request):
        user = self.get_object()
        if user.is_superuser and not request.user.is_superuser:
            return False
        return super().has_model_permission(request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        context.update(
            {
                "permission_actions": permission_action_labels(),
                "permission_rows": user_permission_rows(user),
                "group_permissions": group_permission_map(),
                "date_joined": format_datetime(user.date_joined),
                "last_login": format_last_login(user.last_login),
                "is_own_account": context["form"].is_own_account(),
            }
        )
        return context

    def update_object(self, form):
        user = form.save()
        if form.cleaned_data.get("password") and user.pk == self.request.user.pk:
            update_session_auth_hash(self.request, user)
        return user


# endregion
"""========================================================================="""
