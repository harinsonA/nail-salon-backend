from rest_framework import serializers

from apps.payments.models import DetallePago


class AppointmentPrepaidSerializer(serializers.ModelSerializer):
    monto_pago = serializers.IntegerField()

    class Meta:
        model = DetallePago
        fields = [
            "id",
            "tipo_detalle",
            "monto_pago",
            "metodo_pago",
            "referencia_pago",
            "fecha_pago",
        ]
