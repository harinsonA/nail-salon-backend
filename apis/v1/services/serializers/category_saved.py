from rest_framework import serializers

from apis.v1.sync.serializers import CategorySerializer


class CategorySavedSerializer(serializers.Serializer):
    message = serializers.CharField()
    category = CategorySerializer()
