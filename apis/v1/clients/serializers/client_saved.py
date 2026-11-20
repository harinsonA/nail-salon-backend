from rest_framework import serializers

from apis.v1.sync.serializers import ClientSerializer


class ClientSavedSerializer(serializers.Serializer):
    message = serializers.CharField()
    client = ClientSerializer()
