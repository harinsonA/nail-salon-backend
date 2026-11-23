from rest_framework import serializers


class DetailStatusSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
