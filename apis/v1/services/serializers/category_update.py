from rest_framework import serializers

from apps.services.models import Categoria

from .category_fields import CategoryFieldsSerializer


class CategoryUpdateSerializer(CategoryFieldsSerializer):
    estado = serializers.ChoiceField(choices=Categoria.EstadoChoices.choices, required=False)
    version = serializers.DateTimeField(required=False, allow_null=True)
