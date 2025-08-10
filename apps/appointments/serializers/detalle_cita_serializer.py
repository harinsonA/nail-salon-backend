from rest_framework import serializers
from ..models.detalle_cita import DetalleCita


class DetalleCitaSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo DetalleCita
    """

    # Añadir campo 'id' para compatibilidad con API REST estándar
    id = serializers.IntegerField(source="detalle_cita_id", read_only=True)

    # Campos calculados
    subtotal = serializers.ReadOnlyField()
    precio_unitario_con_descuento = serializers.ReadOnlyField()

    # Información del servicio anidada (solo lectura)
    servicio_nombre = serializers.CharField(
        source="servicio.nombre_servicio", read_only=True
    )
    servicio_precio = serializers.DecimalField(
        source="servicio.precio", max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = DetalleCita
        fields = [
            "id",
            "detalle_cita_id",
            "cita",
            "servicio",
            "servicio_nombre",
            "servicio_precio",
            "precio_acordado",
            "cantidad_servicios",
            "descuento",
            "subtotal",
            "precio_unitario_con_descuento",
            "notas_detalle",
            "fecha_creacion",
        ]
        read_only_fields = [
            "id",
            "detalle_cita_id",
            "subtotal",
            "precio_unitario_con_descuento",
            "servicio_nombre",
            "servicio_precio",
            "fecha_creacion",
        ]

    def validate_cantidad_servicios(self, value):
        """
        Validar que la cantidad de servicios sea positiva
        """
        if value <= 0:
            raise serializers.ValidationError(
                "La cantidad de servicios debe ser mayor a 0."
            )
        return value

    def validate_descuento(self, value):
        """
        Validar que el descuento esté en el rango válido
        """
        if value < 0:
            raise serializers.ValidationError("El descuento no puede ser negativo.")
        if value > 100:
            raise serializers.ValidationError(
                "El descuento no puede ser mayor al 100%."
            )
        return value

    def validate(self, attrs):
        """
        Validación a nivel de objeto
        """
        # Validar que no se duplique el servicio en la misma cita
        cita = attrs.get("cita")
        servicio = attrs.get("servicio")

        if cita and servicio:
            # Si estamos creando (no hay instance) o editando servicio
            if not self.instance or self.instance.servicio != servicio:
                if DetalleCita.objects.filter(cita=cita, servicio=servicio).exists():
                    raise serializers.ValidationError(
                        "Este servicio ya está agregado a la cita."
                    )

        return attrs
