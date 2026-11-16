from rest_framework import serializers


class PasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False, default="")
    new_password = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False, default="")
    confirm_password = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False, default="")


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField()
