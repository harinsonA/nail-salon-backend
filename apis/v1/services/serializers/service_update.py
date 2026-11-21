from rest_framework import serializers

from apps.services.models import Servicio

from .service_fields import ServiceFieldsSerializer


class ServiceUpdateSerializer(ServiceFieldsSerializer):
    estado = serializers.ChoiceField(choices=Servicio.EstadoChoices.choices, required=False)
    version = serializers.DateTimeField(required=False, allow_null=True)
