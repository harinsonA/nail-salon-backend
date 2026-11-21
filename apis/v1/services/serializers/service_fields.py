from rest_framework import serializers


class ServiceFieldsSerializer(serializers.Serializer):
    categoria_id = serializers.IntegerField(required=False, allow_null=True)
    nombre = serializers.CharField(required=False, allow_blank=True)
    precio = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    duracion_estimada = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    descripcion = serializers.CharField(required=False, allow_blank=True, allow_null=True)
