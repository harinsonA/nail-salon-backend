from rest_framework import serializers
from ..models.servicio import Servicio


class ServicioSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Servicio
    """

    duracion_estimada_horas = serializers.SerializerMethodField()
    precio_formateado = serializers.SerializerMethodField()

    class Meta:
        model = Servicio
        fields = [
            "servicio_id",
            "nombre_servicio",
            "precio",
            "precio_formateado",
            "descripcion",
            "duracion_estimada",
            "duracion_estimada_horas",
            "activo",
            "categoria",
            "imagen",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = ["servicio_id", "fecha_creacion", "fecha_actualizacion"]

    def get_duracion_estimada_horas(self, obj):
        """
        Convertir duración a formato legible
        """
        if obj.duracion_estimada:
            total_seconds = obj.duracion_estimada.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            return f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        return "No especificado"

    def get_precio_formateado(self, obj):
        """
        Formatear precio con símbolo de moneda
        """
        return f"${obj.precio:,.2f}"

    def validate_precio(self, value):
        """
        Validar que el precio sea mayor a 0
        """
        if value <= 0:
            raise serializers.ValidationError("El precio debe ser mayor a 0.")
        return value

    def validate_duracion_estimada(self, value):
        """
        Validar duración estimada
        """
        if value and value.total_seconds() <= 0:
            raise serializers.ValidationError(
                "La duración estimada debe ser mayor a 0."
            )
        return value


class ServicioListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listas de servicios
    """

    precio_formateado = serializers.SerializerMethodField()
    duracion_estimada_horas = serializers.SerializerMethodField()

    class Meta:
        model = Servicio
        fields = [
            "servicio_id",
            "nombre_servicio",
            "precio_formateado",
            "duracion_estimada_horas",
            "categoria",
            "activo",
        ]

    def get_precio_formateado(self, obj):
        return f"${obj.precio:,.2f}"

    def get_duracion_estimada_horas(self, obj):
        if obj.duracion_estimada:
            total_seconds = obj.duracion_estimada.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            return f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        return "No especificado"
