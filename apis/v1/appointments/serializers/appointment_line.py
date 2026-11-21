from rest_framework import serializers


class AppointmentLineSerializer(serializers.Serializer):
    servicio_id = serializers.IntegerField(required=False, allow_null=True)
    detalle_id = serializers.IntegerField(required=False, allow_null=True)
    cantidad_servicios = serializers.IntegerField(required=False, default=1)
    descuento = serializers.IntegerField(required=False, default=0)
    precio_servicio = serializers.IntegerField(required=False, allow_null=True)
