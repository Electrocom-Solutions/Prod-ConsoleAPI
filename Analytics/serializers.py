from rest_framework import serializers
from AMC.models import AMC
from Analytics.models import ActivityLog


class ExpiringAMCSerializer(serializers.Serializer):
    client_name = serializers.CharField()
    amc_expiry_date = serializers.DateField()
    expiry_count_days = serializers.IntegerField()
    amc_number = serializers.CharField()


class RecentActivitySerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = ActivityLog
        fields = ['id', 'entity_type', 'entity_id', 'action', 'description', 'created_at', 'created_by', 'created_by_username']


class DashboardStatsSerializer(serializers.Serializer):
    total_clients = serializers.IntegerField()
    active_amcs_count = serializers.IntegerField()
    active_tenders_count = serializers.IntegerField()
    in_progress_tasks_count = serializers.IntegerField()
    expiring_amcs = ExpiringAMCSerializer(many=True)
    recent_activities = RecentActivitySerializer(many=True)
