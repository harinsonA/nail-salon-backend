from rest_framework import serializers


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.CharField()
    username = serializers.CharField()
    initials = serializers.CharField()
    rol = serializers.CharField()
    pais = serializers.CharField(allow_null=True)
    tipo_identificador_nacional = serializers.CharField(allow_null=True)
    identificador_nacional = serializers.CharField(allow_null=True)
