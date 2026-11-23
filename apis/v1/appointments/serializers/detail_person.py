from rest_framework import serializers


class DetailPersonSerializer(serializers.Serializer):
    name = serializers.CharField()
    when = serializers.CharField()
