from rest_framework import serializers

from apis.v1.me.serializers.assignable_user import AssignableUserSerializer
from apis.v1.me.serializers.preferences import PreferencesSerializer
from apis.v1.me.serializers.user import UserSerializer


class MeSerializer(serializers.Serializer):
    user = UserSerializer()
    can_edit_profile = serializers.BooleanField()
    capabilities = serializers.ListField(child=serializers.CharField())
    assignable_users = AssignableUserSerializer(many=True)
    preferences = PreferencesSerializer()
