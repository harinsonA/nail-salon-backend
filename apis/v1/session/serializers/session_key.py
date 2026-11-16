from rest_framework import serializers


class SessionKeySerializer(serializers.Serializer):
    session_key = serializers.CharField()
    expires_at = serializers.DateTimeField()
    temporary_password = serializers.BooleanField()
    biometric = serializers.BooleanField()
