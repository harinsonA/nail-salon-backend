from rest_framework import serializers


class BusinessSerializer(serializers.Serializer):
    nombre = serializers.CharField()
    estado = serializers.CharField()
    overdue = serializers.BooleanField()


class MaintenanceSerializer(serializers.Serializer):
    active = serializers.BooleanField()
    message = serializers.CharField(allow_null=True)


class VersionSerializer(serializers.Serializer):
    minimum = serializers.CharField(allow_null=True)
    latest = serializers.CharField(allow_null=True)


class StartupSerializer(serializers.Serializer):
    business = BusinessSerializer()
    app_enabled = serializers.BooleanField()
    maintenance = MaintenanceSerializer()
    version = VersionSerializer()
    currency = serializers.CharField()
    zona_horaria = serializers.CharField()
