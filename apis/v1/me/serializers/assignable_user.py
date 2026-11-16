from rest_framework import serializers


class AssignableUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
