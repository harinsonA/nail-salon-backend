from rest_framework import serializers


class PrepaidRowSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField()
    kind = serializers.CharField()
    reservation = serializers.BooleanField()
    discounts = serializers.BooleanField()
    method = serializers.CharField()
    method_label = serializers.CharField()
    date = serializers.CharField()
