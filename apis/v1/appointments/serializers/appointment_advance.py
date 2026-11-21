from rest_framework import serializers


class AppointmentAdvanceSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    monto_pago = serializers.IntegerField(required=False, allow_null=True)
    metodo_pago = serializers.CharField(required=False, allow_blank=True)
    referencia_pago = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    remove = serializers.BooleanField(required=False, default=False)
