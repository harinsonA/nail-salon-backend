from rest_framework import serializers


class CompletionReservationSerializer(serializers.Serializer):
    label = serializers.CharField()
    amount = serializers.IntegerField()
    discounts = serializers.BooleanField()
