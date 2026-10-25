from bootstrap_modal_forms.forms import BSModalForm
from bootstrap_modal_forms.generic import BSModalFormView
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, F, Q, TextChoices, Value
from django.db.models.functions import Concat, Trim
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView
from rest_framework.status import HTTP_400_BAD_REQUEST

from apps.common.base_list_view_ajax import BaseListViewAjax
from apps.common.claves import generar_clave_temporal
from apps.common.form_classes import FORM_CONTROL_CLASS, FORM_SELECT_CLASS
from apps.common.form_fields import AlphabeticField
from apps.common.forms import NationalIdentifierForm
from apps.common.utils.search import search_ignoring_accents
from apps.common.utils.text import user_display_name
from apps.common.utils.utils import CommonCleaner, get_errors_to_response
from apps.common.views.base_views import ProtectedView
from apps.profiles.models import Perfil
from apps.profiles.permisos import puede_gestionar, roles_que_puede_crear
from apps.seguridad.access import (
    LOCK_FREE,
    describe_lock,
    format_lock,
    lock_status,
    locked_users_filter,
    unlock,
    with_lock_level,
)

"""========================================================================="""
# region ........ Constants


User = get_user_model()

ALL = "all"
NAME_MAX_LENGTH = 150
EMAIL_MAX_LENGTH = 254
UNLOCK_REASON = "Desbloqueado desde Equipo"
RESET_UNLOCK_REASON = "Desbloqueado al restablecer la clave desde Equipo"
ROLE_LABELS = dict(Perfil.Rol.choices)


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Helpers


def assign_temporary_password(member):
    password = generar_clave_temporal()
    member.set_password(password)
    member.save()
    Perfil.objects.filter(user=member).update(debe_cambiar_clave=True)
    unlock(member, RESET_UNLOCK_REASON)
    return password


def member_options(item):
    options = [
        {
            "label": "Editar",
            "link": reverse("equipo_editar", args=[item["pk"]]),
            "bsModal": True,
            "icon": "edit_document",
            "className": "bs-modal",
        }
    ]
    if item["lock"] != LOCK_FREE:
        options.append(
            {
                "label": "Desbloquear",
                "link": reverse("equipo_desbloquear", args=[item["pk"]]),
                "bsModal": True,
                "icon": "lock_open",
                "className": "bs-modal",
            }
        )
    options.extend(
        [
            {
                "label": "Restablecer clave",
                "link": reverse("equipo_restablecer_clave", args=[item["pk"]]),
                "bsModal": True,
                "icon": "key",
                "className": "bs-modal",
            },
            {
                "label": "Desactivar" if item["is_active"] else "Reactivar",
                "link": reverse("equipo_activar", args=[item["pk"]]),
                "bsModal": True,
                "icon": "person_off" if item["is_active"] else "person_check",
                "className": (
                    "bs-modal text-color-destructive"
                    if item["is_active"]
                    else "bs-modal"
                ),
            },
        ]
    )
    return options


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Mixins


class ManagedMemberMixin:
    def get_member(self):
        if not hasattr(self, "_member"):
            member = get_object_or_404(
                User.objects.select_related("perfil"), pk=self.kwargs["pk"]
            )
            if not puede_gestionar(self.request.user, member):
                raise PermissionDenied
            self._member = member
        return self._member


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Forms


class MemberForm(NationalIdentifierForm, BSModalForm):
    national_id_required = True
    national_id_holder = "otra persona de este negocio"

    first_name = AlphabeticField(
        label="Nombre",
        max_length=NAME_MAX_LENGTH,
        widget=forms.TextInput(attrs={"class": FORM_CONTROL_CLASS, "placeholder": "Ana"}),
    )
    last_name = AlphabeticField(
        label="Apellido",
        max_length=NAME_MAX_LENGTH,
        required=False,
        widget=forms.TextInput(attrs={"class": FORM_CONTROL_CLASS, "placeholder": "Rojas"}),
    )
    email = forms.EmailField(
        label="Correo",
        max_length=EMAIL_MAX_LENGTH,
        help_text="Con este correo entra a la agenda.",
        widget=forms.EmailInput(
            attrs={"class": FORM_CONTROL_CLASS, "placeholder": "ana.rojas@correo.cl"}
        ),
    )
    rol = forms.ChoiceField(
        label="Rol",
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )

    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        if instance:
            kwargs["initial"] = {
                **self.national_id_initial(instance.perfil),
                **kwargs.get("initial", {}),
            }
        super().__init__(*args, **kwargs)
        self.fields["rol"].choices = [
            (rol.value, rol.label) for rol in roles_que_puede_crear(self.request.user)
        ]
        if instance:
            self.initial.update(
                {
                    "first_name": instance.first_name,
                    "last_name": instance.last_name,
                    "email": instance.email,
                    "rol": instance.perfil.rol,
                }
            )

    def national_id_queryset(self):
        profiles = Perfil.objects.all()
        return profiles.exclude(user=self.instance) if self.instance else profiles

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        others = User.objects.all()
        if self.instance:
            others = others.exclude(pk=self.instance.pk)
        result = CommonCleaner.check_email_available(others, self.national_id_holder, email)
        if result.is_err():
            raise forms.ValidationError(result.err_value)
        return email

    @transaction.atomic
    def save(self):
        data = self.cleaned_data
        member = self.instance or User()
        member.username = data["email"][:NAME_MAX_LENGTH]
        member.email = data["email"]
        member.first_name = data["first_name"]
        member.last_name = data["last_name"]
        if not member.pk:
            member.set_unusable_password()
        member.save()
        perfil = self.instance.perfil if self.instance else Perfil.objects.get(user=member)
        self.save_national_id(perfil, rol=data["rol"])
        return member


class TeamFilterForm(forms.Form):
    class StatusChoices(TextChoices):
        ALL = ALL, "Todos"
        ACTIVE = "active", "Activos"
        INACTIVE = "inactive", "Inactivos"
        LOCKED = "locked", "Bloqueados"

    status = forms.ChoiceField(
        choices=StatusChoices.choices,
        label="Estado",
        initial=StatusChoices.ALL,
        required=False,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    role = forms.ChoiceField(
        choices=[(ALL, "Todos"), *Perfil.Rol.choices],
        label="Rol",
        initial=ALL,
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
        elif status == self.StatusChoices.LOCKED:
            filters["lock__gt"] = LOCK_FREE
        role = cleaned_data.get("role")
        if role and role != ALL:
            filters["perfil__rol"] = role
        return filters


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class TeamView(ProtectedView, TemplateView):
    template_name = "equipo/lista.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "filter_form": TeamFilterForm(),
                "list_url": reverse("equipo_lista"),
                "can_create": bool(roles_que_puede_crear(self.request.user)),
            }
        )
        return context


class TeamListView(BaseListViewAjax):
    model = User
    filter_form_class = TeamFilterForm
    field_list = [
        "pk",
        "full_name",
        "email",
        "rol",
        "is_active",
        "lock",
        "lock_until",
    ]
    ordering_fields = {
        "0": "full_name",
        "1": "email",
        "2": "rol",
        "3": "is_active",
        "4": "lock",
    }

    def get_queryset(self):
        members = User.objects.annotate(
            full_name=Trim(Concat("first_name", Value(" "), "last_name")),
            rol=F("perfil__rol"),
        )
        return with_lock_level(members, timezone.now()).filter(**self.get_filters())

    def get_filter_by_search(self):
        search_value = self.request.GET.get("search[value]", "")
        if not search_value:
            return Q()
        return (
            search_ignoring_accents(["first_name", "last_name", "email"], search_value)
        )

    def get_values(self, queryset):
        values = super().get_values(queryset)
        for value in values:
            value["full_name"] = value["full_name"] or "—"
            value["role_label"] = ROLE_LABELS.get(value["rol"], "—")
            value["lock_label"] = format_lock(value["lock"], value.pop("lock_until"))
        return values

    def add_options_column(self, data):
        members = User.objects.select_related("perfil").in_bulk(
            [item["pk"] for item in data]
        )
        for item in data:
            item["options"] = (
                member_options(item)
                if puede_gestionar(self.request.user, members[item["pk"]])
                else []
            )
        return data

    @staticmethod
    def additional_data(queryset):
        return User.objects.aggregate(
            active_members=Count("pk", filter=Q(is_active=True)),
            inactive_members=Count("pk", filter=Q(is_active=False)),
            locked_members=Count("pk", filter=locked_users_filter(timezone.now())),
        )


class MemberFormModalView(ProtectedView, BSModalFormView):
    template_name = "equipo/member_modal.html"
    form_class = MemberForm

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "modal_url": self.request.path}

    def form_invalid(self, form):
        return JsonResponse(
            {"errors": get_errors_to_response(form.errors)}, status=HTTP_400_BAD_REQUEST
        )


class MemberCreateModalView(MemberFormModalView):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not roles_que_puede_crear(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        member = form.save()
        password = assign_temporary_password(member)
        response = JsonResponse(
            {
                "message": f"{user_display_name(member)} quedó creado.",
                "email": member.email,
                "password": password,
            }
        )
        response["Cache-Control"] = "no-store"
        return response


class MemberUpdateModalView(ManagedMemberMixin, MemberFormModalView):
    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "instance": self.get_member()}

    def get_context_data(self, **kwargs):
        member = self.get_member()
        return {
            **super().get_context_data(**kwargs),
            "member": member,
            "member_name": user_display_name(member),
        }

    def form_valid(self, form):
        member = form.save()
        return JsonResponse({"message": f"{user_display_name(member)} quedó actualizado."})


class MemberActionModalView(ProtectedView, ManagedMemberMixin, TemplateView):
    def get_context_data(self, **kwargs):
        member = self.get_member()
        return {
            **super().get_context_data(**kwargs),
            "modal_url": self.request.path,
            "member": member,
            "member_name": user_display_name(member),
            "role_label": member.perfil.get_rol_display(),
        }


class MemberActiveModalView(MemberActionModalView):
    template_name = "equipo/active_modal.html"

    def post(self, request, *args, **kwargs):
        member = self.get_member()
        member.is_active = not member.is_active
        member.save(update_fields=["is_active"])
        action = "reactivado" if member.is_active else "desactivado"
        return JsonResponse({"message": f"{user_display_name(member)} quedó {action}."})


class MemberUnlockModalView(MemberActionModalView):
    template_name = "equipo/unlock_modal.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status = lock_status(context["member"])
        return {**context, "status": status, "lock_description": describe_lock(status)}

    def post(self, request, *args, **kwargs):
        member = self.get_member()
        name = user_display_name(member)
        if not unlock(member, UNLOCK_REASON):
            return JsonResponse(
                {"message": f"{name} no estaba bloqueado."},
                status=HTTP_400_BAD_REQUEST,
            )
        return JsonResponse(
            {"message": f"{name} quedó desbloqueado: ya puede entrar con su clave actual."}
        )


class MemberPasswordResetModalView(MemberActionModalView):
    template_name = "equipo/password_modal.html"

    def post(self, request, *args, **kwargs):
        member = self.get_member()
        password = assign_temporary_password(member)
        response = JsonResponse(
            {
                "message": "Se generó una clave temporal nueva.",
                "email": member.email,
                "password": password,
            }
        )
        response["Cache-Control"] = "no-store"
        return response


# endregion
"""========================================================================="""
