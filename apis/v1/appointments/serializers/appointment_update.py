from rest_framework import serializers

from .appointment_fields import AppointmentFieldsSerializer


class AppointmentUpdateSerializer(AppointmentFieldsSerializer):
    version = serializers.DateTimeField(required=False, allow_null=True)
