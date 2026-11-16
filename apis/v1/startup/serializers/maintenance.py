from rest_framework import serializers


class MaintenanceSerializer(serializers.Serializer):
    active = serializers.BooleanField()
    message = serializers.CharField(allow_null=True)
