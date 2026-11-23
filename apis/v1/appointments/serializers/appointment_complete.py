from rest_framework import serializers


class AppointmentCompleteSerializer(serializers.Serializer):
    full_payment = serializers.BooleanField()
    monto_pago = serializers.IntegerField(required=False, allow_null=True)
    metodo_pago = serializers.CharField(required=False, allow_blank=True)
    referencia_pago = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    notas_detalle = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    remaining = serializers.IntegerField()
