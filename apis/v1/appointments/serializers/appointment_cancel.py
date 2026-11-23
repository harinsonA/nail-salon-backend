from rest_framework import serializers

from .appointment_refund import AppointmentRefundSerializer
from .prepaid_seen import PrepaidSeenSerializer


class AppointmentCancelSerializer(serializers.Serializer):
    refunds = AppointmentRefundSerializer(many=True)
    seen = PrepaidSeenSerializer(many=True)
