from rest_framework import serializers

from apps.services.models import Servicio

from .minutes import MinutesField


class ServiceSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk")
    precio = serializers.IntegerField()
    duracion_estimada = MinutesField()

    class Meta:
        model = Servicio
        fields = [
            "id",
            "estado",
            "nombre",
            "precio",
            "descripcion",
            "duracion_estimada",
            "categoria_id",
            "modified",
        ]
