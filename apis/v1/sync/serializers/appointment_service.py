from rest_framework import serializers

from apps.appointments.models import DetalleCita

from .minutes import MinutesField


class AppointmentServiceSerializer(serializers.ModelSerializer):
    precio_servicio = serializers.IntegerField()
    precio_acordado = serializers.IntegerField()
    descuento = serializers.IntegerField()
    duracion_estimada_servicio = MinutesField()

    class Meta:
        model = DetalleCita
        fields = [
            "id",
            "servicio_id",
            "nombre_servicio",
            "precio_servicio",
            "duracion_estimada_servicio",
            "cantidad_servicios",
            "descuento",
            "precio_acordado",
            "notas_detalle",
        ]
