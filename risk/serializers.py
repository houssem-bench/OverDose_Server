from rest_framework import serializers


class RiskRequestSerializer(serializers.Serializer):
    scan_id = serializers.IntegerField()
    ingredients = serializers.ListField(child=serializers.CharField(), allow_empty=True)


class RiskItemSerializer(serializers.Serializer):
    ingredient = serializers.CharField()
    level = serializers.ChoiceField(choices=["low", "medium", "high"])


class RiskResponseSerializer(serializers.Serializer):
    scan_id = serializers.IntegerField()
    risks = RiskItemSerializer(many=True)