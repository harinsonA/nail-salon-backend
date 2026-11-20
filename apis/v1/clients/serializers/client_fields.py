from rest_framework import serializers


class ClientFieldsSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    second_name = serializers.CharField(required=False, allow_blank=True)
    first_surname = serializers.CharField(required=False, allow_blank=True)
    second_surname = serializers.CharField(required=False, allow_blank=True)
    phone_prefix = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.CharField(required=False, allow_blank=True)
    pais = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tipo_identificador_nacional = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    identificador_nacional = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    notas = serializers.CharField(required=False, allow_blank=True, allow_null=True)
