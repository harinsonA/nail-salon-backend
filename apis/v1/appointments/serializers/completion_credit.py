from rest_framework import serializers


class CompletionCreditSerializer(serializers.Serializer):
    label = serializers.CharField()
    amount = serializers.IntegerField()
