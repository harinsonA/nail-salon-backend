from rest_framework import serializers

from .prepaid_row import PrepaidRowSerializer
from .refund_method import RefundMethodSerializer


class CancellationCardSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField(allow_null=True)
    hint = serializers.CharField(allow_null=True)
    locked = serializers.BooleanField()
    locked_message = serializers.CharField(allow_null=True)
    rows = PrepaidRowSerializer(many=True)
    refund_methods = RefundMethodSerializer(many=True)
    cash = serializers.CharField()
    transfer = serializers.CharField()
    reference_max_length = serializers.IntegerField()
