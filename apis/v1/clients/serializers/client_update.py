from rest_framework import serializers

from apps.clients.models import Cliente

from .client_fields import ClientFieldsSerializer


class ClientUpdateSerializer(ClientFieldsSerializer):
    estado = serializers.ChoiceField(choices=Cliente.EstadoChoices.choices, required=False)
    version = serializers.DateTimeField(required=False, allow_null=True)
