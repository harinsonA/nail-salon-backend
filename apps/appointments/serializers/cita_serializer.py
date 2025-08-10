from rest_framework import serializers
from django.utils import timezone
from ..models.cita import Cita
from .detalle_cita_serializer import DetalleCitaSerializer


class CitaSerializer(serializers.ModelSerializer):
    """
    Serializer completo para el modelo Cita
    """

    # Añadir campo 'id' para compatibilidad con API REST estándar
    id = serializers.IntegerField(source="cita_id", read_only=True)

    # Campos calculados
    monto_total = serializers.ReadOnlyField()
    duracion_total = serializers.ReadOnlyField()
    puede_ser_modificada = serializers.ReadOnlyField()

    # Información del cliente anidada (solo lectura)
    cliente_nombre = serializers.CharField(
        source="cliente.nombre_completo", read_only=True
    )
    cliente_telefono = serializers.CharField(source="cliente.telefono", read_only=True)
    cliente_email = serializers.CharField(source="cliente.email", read_only=True)

    # Información del usuario que creó (solo lectura)
    creado_por_username = serializers.CharField(
        source="creado_por.username", read_only=True
    )

    # Detalles de la cita anidados
    detalles = DetalleCitaSerializer(many=True, read_only=True)

    class Meta:
        model = Cita
        fields = [
            "id",
            "cita_id",
            "cliente",
            "cliente_nombre",
            "cliente_telefono",
            "cliente_email",
            "fecha_hora_cita",
            "estado_cita",
            "observaciones",
            "monto_total",
            "duracion_total",
            "puede_ser_modificada",
            "detalles",
            "fecha_creacion",
            "fecha_actualizacion",
            "creado_por",
            "creado_por_username",
        ]
        read_only_fields = [
            "id",
            "cita_id",
            "cliente_nombre",
            "cliente_telefono",
            "cliente_email",
            "monto_total",
            "duracion_total",
            "puede_ser_modificada",
            "detalles",
            "fecha_creacion",
            "fecha_actualizacion",
            "creado_por_username",
        ]

    def validate_fecha_hora_cita(self, value):
        """
        Validar que la fecha de la cita no sea en el pasado
        """
        if value <= timezone.now():
            raise serializers.ValidationError(
                "La fecha y hora de la cita debe ser en el futuro."
            )
        return value

    def validate_cliente(self, value):
        """
        Validar que el cliente esté activo
        """
        if not value.activo:
            raise serializers.ValidationError(
                "No se puede agendar cita para un cliente inactivo."
            )
        return value

    def validate(self, attrs):
        """
        Validaciones a nivel de objeto
        """
        estado_cita = attrs.get("estado_cita")

        # Si estamos actualizando una cita existente
        if self.instance:
            # No permitir cambios si la cita ya está completada o cancelada
            if self.instance.estado_cita in ["COMPLETADA", "CANCELADA"]:
                if estado_cita and estado_cita != self.instance.estado_cita:
                    raise serializers.ValidationError(
                        "No se puede modificar una cita completada o cancelada."
                    )

        return attrs

    def create(self, validated_data):
        """
        Personalizar la creación de citas
        """
        # Asignar el usuario que está creando la cita
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["creado_por"] = request.user

        return super().create(validated_data)


class CitaListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listas de citas
    """

    # Añadir campo 'id' para compatibilidad con API REST estándar
    id = serializers.IntegerField(source="cita_id", read_only=True)

    # Información básica del cliente
    cliente_nombre = serializers.CharField(
        source="cliente.nombre_completo", read_only=True
    )
    cliente_telefono = serializers.CharField(source="cliente.telefono", read_only=True)

    # Campos calculados básicos
    monto_total = serializers.ReadOnlyField()
    duracion_total = serializers.ReadOnlyField()

    # Conteo de servicios
    cantidad_servicios = serializers.SerializerMethodField()

    class Meta:
        model = Cita
        fields = [
            "id",
            "cita_id",
            "cliente",
            "cliente_nombre",
            "cliente_telefono",
            "fecha_hora_cita",
            "estado_cita",
            "monto_total",
            "duracion_total",
            "cantidad_servicios",
            "observaciones",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def get_cantidad_servicios(self, obj):
        """
        Obtener la cantidad total de servicios en la cita
        """
        return obj.detalles.count()
