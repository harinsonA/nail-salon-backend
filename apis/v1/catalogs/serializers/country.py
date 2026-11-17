from rest_framework import serializers

from apis.v1.catalogs.serializers.choice import ChoiceSerializer


class CountrySerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    identifier_types = ChoiceSerializer(many=True)
