from rest_framework import serializers

from apps.payments.choices import MetodoPago


class ReservationSerializer(serializers.Serializer):
    enabled = serializers.BooleanField(required=False)
    amount = serializers.IntegerField(required=False, allow_null=True)
    discounts_total = serializers.BooleanField(required=False)
    payment_method = serializers.ChoiceField(
        choices=MetodoPago.CHOICES, required=False, allow_blank=True, allow_null=True
    )
