from rest_framework import serializers
from ..models.cliente import Cliente


class ClienteSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Cliente
    """

    # Añadir campo 'id' para compatibilidad con API REST estándar
    id = serializers.IntegerField(source="cliente_id", read_only=True)
    # Añadir campo nombre_completo como propiedad
    nombre_completo = serializers.ReadOnlyField()

    class Meta:
        model = Cliente
        fields = [
            "id",
            "cliente_id",
            "nombre",
            "apellido",
            "nombre_completo",
            "telefono",
            "email",
            "fecha_registro",
            "activo",
            "notas",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "cliente_id",
            "nombre_completo",
            "fecha_registro",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def validate_email(self, value):
        """
        Validar que el email sea único
        """
        if Cliente.objects.filter(email=value).exists():
            if self.instance and self.instance.email == value:
                return value
            raise serializers.ValidationError("Ya existe un cliente con este email.")
        return value

    def validate_telefono(self, value):
        """
        Validar formato del teléfono
        """
        if not value.replace("+", "").replace("-", "").replace(" ", "").isdigit():
            raise serializers.ValidationError(
                "El teléfono debe contener solo números, espacios, guiones o el símbolo +."
            )
        return value


class ClienteListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listas de clientes
    """

    # Añadir campo 'id' para compatibilidad con API REST estándar
    id = serializers.IntegerField(source="cliente_id", read_only=True)
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = Cliente
        fields = [
            "id",
            "cliente_id",
            "nombre",
            "apellido",
            "nombre_completo",
            "telefono",
            "email",
            "fecha_registro",
            "activo",
            "notas",
        ]

    def get_nombre_completo(self, obj):
        return f"{obj.nombre} {obj.apellido}"
