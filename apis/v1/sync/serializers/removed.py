from rest_framework import serializers


class RemovedSerializer(serializers.Serializer):
    appointments = serializers.ListField(child=serializers.IntegerField())
    clients = serializers.ListField(child=serializers.IntegerField())
    categories = serializers.ListField(child=serializers.IntegerField())
    services = serializers.ListField(child=serializers.IntegerField())
