from rest_framework import serializers

from apis.v1.startup.serializers.business import BusinessSerializer
from apis.v1.startup.serializers.maintenance import MaintenanceSerializer
from apis.v1.startup.serializers.version import VersionSerializer


class StartupSerializer(serializers.Serializer):
    business = BusinessSerializer()
    app_enabled = serializers.BooleanField()
    maintenance = MaintenanceSerializer()
    version = VersionSerializer()
    currency = serializers.CharField()
    zona_horaria = serializers.CharField()
