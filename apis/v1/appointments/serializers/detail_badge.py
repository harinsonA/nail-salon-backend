from rest_framework import serializers


class DetailBadgeSerializer(serializers.Serializer):
    label = serializers.CharField()
    debt = serializers.BooleanField()
