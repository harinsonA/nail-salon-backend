from rest_framework import serializers


class RefundMethodSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()
