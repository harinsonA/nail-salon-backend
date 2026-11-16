from rest_framework import serializers

from apis.v1.me.serializers.user import UserSerializer


class ProfileSavedSerializer(serializers.Serializer):
    message = serializers.CharField()
    user = UserSerializer()
