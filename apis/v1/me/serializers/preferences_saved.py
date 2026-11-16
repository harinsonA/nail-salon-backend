from rest_framework import serializers

from apis.v1.me.serializers.preferences import PreferencesSerializer


class PreferencesSavedSerializer(serializers.Serializer):
    message = serializers.CharField()
    preferences = PreferencesSerializer()
