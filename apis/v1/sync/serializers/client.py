from rest_framework import serializers

from apps.clients.models import Cliente


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = [
            "id",
            "codigo_app",
            "estado",
            "nombre",
            "apellido",
            "telefono",
            "email",
            "pais",
            "tipo_identificador_nacional",
            "identificador_nacional",
            "notas",
            "modified",
        ]
