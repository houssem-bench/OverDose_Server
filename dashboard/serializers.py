from rest_framework import serializers


class DashboardSummarySerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    total_scans = serializers.IntegerField()
    sample_result = serializers.DictField()