from rest_framework import serializers

from .prepaid_row import PrepaidRowSerializer


class RestorationCardSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField(allow_null=True)
    hint = serializers.CharField(allow_null=True)
    locked = serializers.BooleanField()
    locked_message = serializers.CharField(allow_null=True)
    back_label = serializers.CharField(allow_null=True)
    rows = PrepaidRowSerializer(many=True)
    services_total = serializers.IntegerField()
    prepaid = serializers.IntegerField()
