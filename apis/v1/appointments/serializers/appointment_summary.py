from rest_framework import serializers


class AppointmentSummarySerializer(serializers.Serializer):
    subtotal = serializers.IntegerField()
    discounts = serializers.IntegerField()
    total = serializers.IntegerField()
    reservation = serializers.IntegerField()
    advances = serializers.IntegerField()
    balance = serializers.IntegerField()
