from rest_framework import serializers

from apis.v1.sync.serializers import ServiceSerializer


class ServiceSavedSerializer(serializers.Serializer):
    message = serializers.CharField()
    service = ServiceSerializer()
