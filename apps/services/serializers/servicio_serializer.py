from rest_framework import serializers
from ..models.servicio import Servicio


class ServicioSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Servicio
    """

    # Añadir campo 'id' para compatibilidad con API REST estándar
    id = serializers.IntegerField(source="servicio_id", read_only=True)
    duracion_estimada_horas = serializers.SerializerMethodField()
    precio_formateado = serializers.SerializerMethodField()

    class Meta:
        model = Servicio
        fields = [
            "id",
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
        read_only_fields = [
            "id",
            "servicio_id",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

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

    def validate_nombre_servicio(self, value):
        """
        Validar que el nombre del servicio sea único
        """
        if Servicio.objects.filter(nombre_servicio=value).exists():
            if self.instance and self.instance.nombre_servicio == value:
                return value
            raise serializers.ValidationError("Ya existe un servicio con este nombre.")
        return value

    def validate_precio(self, value):
        """
        Validar que el precio sea mayor o igual a 0
        """
        if value < 0:
            raise serializers.ValidationError("El precio debe ser mayor o igual a 0.")
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

    def to_internal_value(self, data):
        """
        Validar formato de duración antes del parsing
        """
        if "duracion_estimada" in data and isinstance(
            data.get("duracion_estimada"), str
        ):
            duracion_str = data["duracion_estimada"]
            # Verificar formato básico de duración
            if ":" in duracion_str:
                parts = duracion_str.split(":")
                if len(parts) >= 2:
                    try:
                        minutes = int(parts[1]) if len(parts) > 1 else 0
                        seconds = int(parts[2]) if len(parts) > 2 else 0
                        # Validar rangos
                        if minutes > 59 or seconds > 59:
                            raise serializers.ValidationError(
                                {
                                    "duracion_estimada": "Formato de duración inválido. Los minutos y segundos deben ser menores a 60."
                                }
                            )
                    except ValueError:
                        raise serializers.ValidationError(
                            {"duracion_estimada": "Formato de duración inválido."}
                        )
        return super().to_internal_value(data)


class ServicioListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listas de servicios
    """

    # Añadir campo 'id' para compatibilidad con API REST estándar
    id = serializers.IntegerField(source="servicio_id", read_only=True)
    precio_formateado = serializers.SerializerMethodField()
    duracion_estimada_horas = serializers.SerializerMethodField()

    class Meta:
        model = Servicio
        fields = [
            "id",
            "servicio_id",
            "nombre_servicio",
            "precio",
            "precio_formateado",
            "descripcion",
            "duracion_estimada",
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
