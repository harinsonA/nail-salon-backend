from rest_framework import serializers


class MonthSerializer(serializers.Serializer):
    label = serializers.CharField()
    start = serializers.DateField()
    appointments = serializers.IntegerField()
    completed = serializers.IntegerField()
    pending = serializers.IntegerField()
