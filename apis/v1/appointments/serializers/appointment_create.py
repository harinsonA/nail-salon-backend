from rest_framework import serializers

from .appointment_fields import AppointmentFieldsSerializer


class AppointmentCreateSerializer(AppointmentFieldsSerializer):
    codigo_app = serializers.UUIDField(required=False, allow_null=True)
