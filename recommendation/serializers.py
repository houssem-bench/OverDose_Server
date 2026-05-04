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


class RecommendationReportRequestSerializer(serializers.Serializer):
    report_id = serializers.CharField()
    analyzed_at = serializers.CharField()
    agent_version = serializers.CharField()
    depth = serializers.CharField(required=False, allow_blank=True)
    no_dose_data = serializers.BooleanField(required=False)
    products = serializers.ListField(child=serializers.DictField(), allow_empty=True)
    global_summary = serializers.DictField(required=False)
    product_verdicts = serializers.ListField(child=serializers.DictField(), required=False)
    chemicals_summary = serializers.ListField(child=serializers.DictField(), required=False)
    combination_risks = serializers.DictField(required=False)
    scoring_analysis = serializers.DictField(required=False)
    overall_assessment = serializers.CharField(required=False, allow_blank=True)