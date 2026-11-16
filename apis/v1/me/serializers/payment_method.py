from rest_framework import serializers


class PaymentMethodSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()
