from rest_framework import serializers


class PrepaidSeenSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField()
