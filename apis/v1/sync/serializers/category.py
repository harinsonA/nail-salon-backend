from rest_framework import serializers

from apps.services.models import Categoria


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ["id", "estado", "nombre", "descripcion", "modified"]
