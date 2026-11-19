from rest_framework import serializers

from .income import IncomeSerializer
from .month import MonthSerializer


class HomeSerializer(serializers.Serializer):
    month = MonthSerializer()
    debtors = serializers.IntegerField(allow_null=True)
    incomes = IncomeSerializer(many=True, allow_null=True)
