from rest_framework import serializers


class DetailReservationSerializer(serializers.Serializer):
    amount = serializers.CharField()
    status = serializers.CharField()
