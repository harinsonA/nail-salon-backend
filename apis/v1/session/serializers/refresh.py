from rest_framework import serializers


class RefreshSerializer(serializers.Serializer):
    device_key = serializers.CharField()
