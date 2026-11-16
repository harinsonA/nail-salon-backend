from rest_framework import serializers


class ProfileSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.CharField(required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    pais = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tipo_identificador_nacional = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    identificador_nacional = serializers.CharField(required=False, allow_blank=True, allow_null=True)
