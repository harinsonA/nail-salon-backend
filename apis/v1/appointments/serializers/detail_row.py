from rest_framework import serializers


class DetailRowSerializer(serializers.Serializer):
    label = serializers.CharField()
    value = serializers.CharField()
    debt = serializers.BooleanField(default=False)
