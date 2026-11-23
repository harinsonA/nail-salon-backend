from rest_framework import serializers


class DetailPaymentLineSerializer(serializers.Serializer):
    when = serializers.CharField()
    kind = serializers.CharField()
    method = serializers.CharField()
    by = serializers.CharField()
    amount = serializers.CharField()
