from rest_framework import serializers


class MinutesField(serializers.Field):
    def to_representation(self, value):
        return int(value.total_seconds() // 60) if value else None
