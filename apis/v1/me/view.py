from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response

from apis.common import errors
from apis.common.views import ApiView
from apis.v1.me.serializers import (
    MeSerializer,
    PreferencesSavedSerializer,
    PreferencesSerializer,
    ProfileSavedSerializer,
    ProfileSerializer,
)
from apps.common.utils.text import user_display_name
from apps.profiles.capabilities import Capabilities
from apps.profiles.profile import PersonalDataForm, ProfileRules
from apps.settings.preferences.mobile import MobilePreferences
from apps.settings.preferences.registry import (
    APP_CALENDAR_SHOW_CANCELLED,
    APP_CALENDAR_SHOW_COMPLETED,
    APP_CALENDAR_SHOW_DEBT,
    APP_CALENDAR_SHOW_PENDING,
    APP_CALENDAR_VIEW,
    APP_IDLE_LOCK_MINUTES,
    RESERVATION_AMOUNT,
    RESERVATION_DISCOUNTS_TOTAL,
    RESERVATION_ENABLED,
    RESERVATION_PAYMENT_METHOD,
)

"""========================================================================="""
# region ........ Constants


PREFERENCE_KEYS = {
    "calendar_view": APP_CALENDAR_VIEW.key,
    "calendar_show_pending": APP_CALENDAR_SHOW_PENDING.key,
    "calendar_show_completed": APP_CALENDAR_SHOW_COMPLETED.key,
    "calendar_show_cancelled": APP_CALENDAR_SHOW_CANCELLED.key,
    "calendar_show_debt": APP_CALENDAR_SHOW_DEBT.key,
    "idle_lock_minutes": APP_IDLE_LOCK_MINUTES.key,
    "reservation_enabled": RESERVATION_ENABLED.key,
    "reservation_amount": RESERVATION_AMOUNT.key,
    "reservation_discounts_total": RESERVATION_DISCOUNTS_TOTAL.key,
    "reservation_payment_method": RESERVATION_PAYMENT_METHOD.key,
}

PROFILE_FIELDS = {
    "first_name": "first_name",
    "last_name": "last_name",
    "email": "email",
    "pais": "national_id_country",
    "tipo_identificador_nacional": "national_id_type",
    "identificador_nacional": "national_id",
}


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Helpers


def user_data(user):
    rules = ProfileRules(user)
    perfil = rules.perfil
    return {
        "id": user.pk,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "initials": rules.initials,
        "rol": rules.rol,
        "role_label": perfil.get_rol_display() if perfil else None,
        "pais": perfil.pais if perfil else None,
        "tipo_identificador_nacional": perfil.tipo_identificador_nacional if perfil else None,
        "identificador_nacional": perfil.identificador_nacional if perfil else None,
    }


def preferences_data(user):
    values = MobilePreferences(user).values()
    return {name: values[key] for name, key in PREFERENCE_KEYS.items()}


def profile_form_data(user, changes):
    current = user_data(user)
    return {
        form_field: changes.get(field, current[field]) or ""
        for field, form_field in PROFILE_FIELDS.items()
    }


def profile_errors(form):
    api_names = {form_field: field for field, form_field in PROFILE_FIELDS.items()}
    return {api_names.get(name, name): messages for name, messages in form.errors.items()}


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class MeView(ApiView):
    http_method_names = ["get"]

    @extend_schema(
        summary="Perfil, capacidades y preferencias",
        description="Todo lo que la app necesita después de entrar para armar el menú, Opciones y los formularios.",
        responses=MeSerializer,
    )
    def get(self, request, *args, **kwargs):
        user = request.user
        capabilities = Capabilities(user, request.tenant)
        data = {
            "user": user_data(user),
            "can_edit_profile": ProfileRules(user).can_edit_personal_data,
            "capabilities": capabilities.as_list(),
            "assignable_users": [
                {"id": member.pk, "name": user_display_name(member)}
                for member in capabilities.assignable_users()
            ],
            "preferences": preferences_data(user),
        }
        return Response(MeSerializer(data).data)


class ProfileView(ApiView):
    http_method_names = ["patch"]

    @extend_schema(
        summary="Editar Mi perfil",
        description="Solo lo que cambió. Mismas validaciones de la web; la propietaria recibe 403.",
        request=ProfileSerializer,
        responses=ProfileSavedSerializer,
    )
    def patch(self, request, *args, **kwargs):
        user = request.user
        if not ProfileRules(user).can_edit_personal_data:
            raise errors.Forbidden(ProfileRules.LOCKED_MESSAGE)
        serializer = ProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        form = PersonalDataForm(data=profile_form_data(user, serializer.validated_data), instance=user)
        if not form.is_valid():
            raise serializers.ValidationError(profile_errors(form))
        form.save()
        return Response(
            ProfileSavedSerializer({"message": ProfileRules.SAVED_MESSAGE, "user": user_data(user)}).data
        )


class PreferencesView(ApiView):
    http_method_names = ["patch"]

    @extend_schema(
        summary="Editar preferencias de la app",
        description="Solo lo que cambió: calendario de la app y bloqueo por inactividad. La reserva es de solo lectura.",
        request=PreferencesSerializer,
        responses=PreferencesSavedSerializer,
    )
    def patch(self, request, *args, **kwargs):
        serializer = PreferencesSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        MobilePreferences(request.user).update(
            {PREFERENCE_KEYS[name]: value for name, value in serializer.validated_data.items()}
        )
        return Response(
            PreferencesSavedSerializer(
                {"message": MobilePreferences.SAVED_MESSAGE, "preferences": preferences_data(request.user)}
            ).data
        )


# endregion
"""========================================================================="""
