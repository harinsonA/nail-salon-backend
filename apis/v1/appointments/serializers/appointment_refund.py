from rest_framework import serializers


class AppointmentRefundSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    metodo = serializers.CharField()
    referencia = serializers.CharField(required=False, allow_blank=True, allow_null=True)
