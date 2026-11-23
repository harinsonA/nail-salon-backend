from rest_framework import serializers

from .prepaid_seen import PrepaidSeenSerializer


class AppointmentRestoreSerializer(serializers.Serializer):
    restored = serializers.ListField(child=serializers.IntegerField())
    seen = PrepaidSeenSerializer(many=True)
