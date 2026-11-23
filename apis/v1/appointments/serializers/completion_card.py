from rest_framework import serializers

from .completion_credit import CompletionCreditSerializer
from .completion_reservation import CompletionReservationSerializer


class CompletionCardSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    services_total = serializers.IntegerField()
    prepaid = serializers.IntegerField()
    remaining = serializers.IntegerField()
    full_payment_label = serializers.CharField()
    settled_hint = serializers.CharField(allow_null=True)
    blocked = serializers.CharField(allow_null=True)
    credit = CompletionCreditSerializer(many=True)
    reservation = CompletionReservationSerializer(allow_null=True)
    attended_by = serializers.CharField()
