from rest_framework import serializers

from .client_fields import ClientFieldsSerializer


class ClientCreateSerializer(ClientFieldsSerializer):
    codigo_app = serializers.UUIDField(required=False, allow_null=True)
