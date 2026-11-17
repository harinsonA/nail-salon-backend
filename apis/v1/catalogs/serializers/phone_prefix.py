from rest_framework import serializers


class PhonePrefixSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()
    country = serializers.CharField()
