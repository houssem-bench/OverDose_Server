from rest_framework import serializers


class RecommendationRequestSerializer(serializers.Serializer):
    scan_id = serializers.IntegerField()
    risks = serializers.ListField(child=serializers.DictField(), allow_empty=True)


class RecommendationItemSerializer(serializers.Serializer):
    product = serializers.CharField()
    reason = serializers.CharField()


class RecommendationResponseSerializer(serializers.Serializer):
    scan_id = serializers.IntegerField()
    recommendations = RecommendationItemSerializer(many=True)