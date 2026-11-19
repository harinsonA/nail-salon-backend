from rest_framework import serializers


class IncomeSerializer(serializers.Serializer):
    label = serializers.CharField()
    start = serializers.DateField()
    amount = serializers.IntegerField()
