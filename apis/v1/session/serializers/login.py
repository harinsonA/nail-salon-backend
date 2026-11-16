from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=254)
    password = serializers.CharField(trim_whitespace=False)
