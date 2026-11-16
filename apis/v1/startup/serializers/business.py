from rest_framework import serializers


class BusinessSerializer(serializers.Serializer):
    nombre = serializers.CharField()
    estado = serializers.CharField()
    overdue = serializers.BooleanField()
