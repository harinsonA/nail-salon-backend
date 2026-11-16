from rest_framework import serializers

from apps.payments.choices import MetodoPago
from apps.settings.preferences.registry import APP_CALENDAR_VIEW, APP_IDLE_LOCK_MINUTES


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.CharField()
    username = serializers.CharField()
    initials = serializers.CharField()
    rol = serializers.CharField()
    pais = serializers.CharField(allow_null=True)
    tipo_identificador_nacional = serializers.CharField(allow_null=True)
    identificador_nacional = serializers.CharField(allow_null=True)


class AssignableUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class PreferencesSerializer(serializers.Serializer):
    calendar_view = serializers.ChoiceField(choices=APP_CALENDAR_VIEW.choices)
    calendar_show_pending = serializers.BooleanField()
    calendar_show_completed = serializers.BooleanField()
    calendar_show_cancelled = serializers.BooleanField()
    idle_lock_minutes = serializers.ChoiceField(choices=APP_IDLE_LOCK_MINUTES.choices)
    reservation_enabled = serializers.BooleanField(read_only=True)
    reservation_amount = serializers.IntegerField(read_only=True)
    reservation_discounts_total = serializers.BooleanField(read_only=True)
    reservation_payment_method = serializers.ChoiceField(choices=MetodoPago.CHOICES, read_only=True)


class PaymentMethodSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()


class MeSerializer(serializers.Serializer):
    user = UserSerializer()
    can_edit_profile = serializers.BooleanField()
    capabilities = serializers.ListField(child=serializers.CharField())
    assignable_users = AssignableUserSerializer(many=True)
    preferences = PreferencesSerializer()
    payment_methods = PaymentMethodSerializer(many=True)


class ProfileSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.CharField(required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    pais = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tipo_identificador_nacional = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    identificador_nacional = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ProfileSavedSerializer(serializers.Serializer):
    message = serializers.CharField()
    user = UserSerializer()


class PreferencesSavedSerializer(serializers.Serializer):
    message = serializers.CharField()
    preferences = PreferencesSerializer()

