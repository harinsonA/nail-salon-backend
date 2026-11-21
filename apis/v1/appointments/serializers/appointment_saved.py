from rest_framework import serializers

from apis.v1.sync.serializers import AppointmentSerializer


class AppointmentSavedSerializer(serializers.Serializer):
    message = serializers.CharField()
    appointment = AppointmentSerializer()
