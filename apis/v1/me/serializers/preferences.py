from rest_framework import serializers

from apps.payments.choices import MetodoPago
from apps.settings.preferences.registry import APP_CALENDAR_VIEW, APP_IDLE_LOCK_MINUTES


class PreferencesSerializer(serializers.Serializer):
    calendar_view = serializers.ChoiceField(choices=APP_CALENDAR_VIEW.choices)
    calendar_show_pending = serializers.BooleanField()
    calendar_show_completed = serializers.BooleanField()
    calendar_show_cancelled = serializers.BooleanField()
    calendar_show_debt = serializers.BooleanField()
    idle_lock_minutes = serializers.ChoiceField(choices=APP_IDLE_LOCK_MINUTES.choices)
    reservation_enabled = serializers.BooleanField(read_only=True)
    reservation_amount = serializers.IntegerField(read_only=True)
    reservation_discounts_total = serializers.BooleanField(read_only=True)
    reservation_payment_method = serializers.ChoiceField(choices=MetodoPago.CHOICES, read_only=True)
