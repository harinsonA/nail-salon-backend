from rest_framework import serializers

from .appointment import AppointmentSerializer
from .category import CategorySerializer
from .client import ClientSerializer
from .removed import RemovedSerializer
from .service import ServiceSerializer
from .window import WindowSerializer


class ChangesSerializer(serializers.Serializer):
    mark = serializers.CharField()
    full = serializers.BooleanField()
    window = WindowSerializer()
    appointments = AppointmentSerializer(many=True)
    clients = ClientSerializer(many=True)
    categories = CategorySerializer(many=True)
    services = ServiceSerializer(many=True)
    removed = RemovedSerializer()
