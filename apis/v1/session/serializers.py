from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=254)
    password = serializers.CharField(trim_whitespace=False)


class RefreshSerializer(serializers.Serializer):
    device_key = serializers.CharField()


class SessionKeySerializer(serializers.Serializer):
    session_key = serializers.CharField()
    expires_at = serializers.DateTimeField()
    temporary_password = serializers.BooleanField()
    biometric = serializers.BooleanField()


class DeviceKeySerializer(serializers.Serializer):
    device_key = serializers.CharField()
    expires_at = serializers.DateTimeField()
