from rest_framework import serializers


class AppointmentReservationSerializer(serializers.Serializer):
    active = serializers.BooleanField()
    metodo_pago = serializers.CharField(required=False, allow_blank=True)
    referencia_pago = serializers.CharField(required=False, allow_blank=True, allow_null=True)
