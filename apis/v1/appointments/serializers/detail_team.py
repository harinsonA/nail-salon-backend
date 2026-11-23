from rest_framework import serializers


class DetailTeamSerializer(serializers.Serializer):
    label = serializers.CharField()
    name = serializers.CharField()
