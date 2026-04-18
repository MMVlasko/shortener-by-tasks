from django.core.validators import URLValidator
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import Link


class LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Link
        fields = [
            'short', 'original', 'user', 'created_at', 'updated_at'
        ]


class LinkCreateAndUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Link
        fields = [
            'original'
        ]

    @staticmethod
    def validate_original(value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("URL не может быть пустым")

        if not value.startswith(('http://', 'https://')):
            value = 'https://' + value

        validator = URLValidator()
        try:
            validator(value)
        except ValidationError:
            raise serializers.ValidationError("Введите корректный URL")

        return value


class ErrorSerializer(serializers.Serializer):
    error = serializers.CharField()