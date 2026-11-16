from rest_framework import serializers


class DeviceKeySerializer(serializers.Serializer):
    device_key = serializers.CharField()
    expires_at = serializers.DateTimeField()
