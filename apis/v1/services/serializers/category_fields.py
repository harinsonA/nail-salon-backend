from rest_framework import serializers


class CategoryFieldsSerializer(serializers.Serializer):
    nombre = serializers.CharField(required=False, allow_blank=True)
    descripcion = serializers.CharField(required=False, allow_blank=True, allow_null=True)
