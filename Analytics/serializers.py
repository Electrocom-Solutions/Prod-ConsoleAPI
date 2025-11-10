from rest_framework import serializers
from AMC.models import AMC
from Analytics.models import ActivityLog


class ExpiringAMCSerializer(serializers.Serializer):
    client_name = serializers.CharField()
    amc_expiry_date = serializers.DateField()
    expiry_count_days = serializers.IntegerField()
    amc_number = serializers.CharField()


class RecentActivitySerializer(serializers.ModelSerializer):
    created_by_username = serializers.SerializerMethodField()
    
    def get_created_by_username(self, obj):
        """Safely get username from created_by, returning None if created_by is None"""
        return obj.created_by.username if obj.created_by else None
    
    def to_representation(self, instance):
        """Override to ensure created_by is serialized as integer ID, not User object"""
        data = super().to_representation(instance)
        # Explicitly convert created_by to integer ID if it exists
        # Handle both cases: when created_by is already an ID or when it's a User object
        if 'created_by' in data:
            if instance.created_by:
                # Ensure it's an integer, not a User object
                data['created_by'] = int(instance.created_by.id) if hasattr(instance.created_by, 'id') else None
            else:
                data['created_by'] = None
        return data
    
    class Meta:
        model = ActivityLog
        fields = ['id', 'entity_type', 'entity_id', 'action', 'description', 'created_at', 'created_by', 'created_by_username']
        extra_kwargs = {
            'created_by': {'read_only': True}
        }


class DashboardStatsSerializer(serializers.Serializer):
    total_clients = serializers.IntegerField()
    active_amcs_count = serializers.IntegerField()
    active_tenders_count = serializers.IntegerField()
    in_progress_tasks_count = serializers.IntegerField()
    expiring_amcs = ExpiringAMCSerializer(many=True)
    recent_activities = serializers.ListField(child=serializers.DictField(), allow_empty=True)
