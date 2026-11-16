from rest_framework import serializers


class VersionSerializer(serializers.Serializer):
    minimum = serializers.CharField(allow_null=True)
    latest = serializers.CharField(allow_null=True)
