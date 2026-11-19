from rest_framework import serializers


class WindowSerializer(serializers.Serializer):
    start = serializers.DateField()
    end = serializers.DateField()
