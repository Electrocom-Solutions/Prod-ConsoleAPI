from rest_framework import serializers
from .models import Task, TaskAttachment, TaskResource
from Analytics.models import ActivityLog


class TaskAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = TaskAttachment
        fields = [
            'id', 'file', 'file_url', 'file_name', 'notes', 'created_at', 'created_by', 'created_by_username'
        ]
        read_only_fields = ['id', 'created_at', 'created_by']
    
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None
    
    def get_file_name(self, obj):
        if obj.file:
            return obj.file.name.split('/')[-1]
        return None


class TaskResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskResource
        fields = [
            'id', 'resource_name', 'quantity', 'unit_cost', 'total_cost', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ActivityFeedSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = ActivityLog
        fields = [
            'id', 'entity_type', 'entity_id', 'action', 'description',
            'created_at', 'created_by', 'created_by_username'
        ]
        read_only_fields = ['id', 'entity_type', 'entity_id', 'action', 'description', 'created_at', 'created_by']


class TaskListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    project_name = serializers.CharField(source='project.name', read_only=True)
    tender_name = serializers.CharField(source='project.tender.name', read_only=True)
    time_taken_hours = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'task_name', 'deadline', 'location', 'time_taken_minutes',
            'time_taken_hours', 'status', 'approval_status', 'employee', 'employee_name',
            'project', 'project_name', 'tender_name', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_employee_name(self, obj):
        """Get employee name from profile user"""
        if obj.employee and obj.employee.profile and obj.employee.profile.user:
            user = obj.employee.profile.user
            full_name = f"{user.first_name} {user.last_name}".strip()
            return full_name if full_name else user.username
        return None
    
    def get_time_taken_hours(self, obj):
        """Convert minutes to hours"""
        if obj.time_taken_minutes:
            return round(obj.time_taken_minutes / 60.0, 2)
        return 0.0


class TaskDetailSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    project_name = serializers.CharField(source='project.name', read_only=True)
    tender_name = serializers.CharField(source='project.tender.name', read_only=True)
    time_taken_hours = serializers.SerializerMethodField()
    attachments = TaskAttachmentSerializer(many=True, read_only=True)
    resources = TaskResourceSerializer(many=True, read_only=True)
    activity_feed = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    updated_by_username = serializers.CharField(source='updated_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = Task
        fields = [
            'id', 'task_name', 'task_description', 'deadline', 'location',
            'time_taken_minutes', 'time_taken_hours', 'status', 'approval_status', 'internal_notes',
            'employee', 'employee_name', 'project', 'project_name', 'tender_name',
            'attachments', 'resources', 'activity_feed',
            'created_at', 'updated_at', 'created_by', 'created_by_username',
            'updated_by', 'updated_by_username'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def get_employee_name(self, obj):
        """Get employee name from profile user"""
        if obj.employee and obj.employee.profile and obj.employee.profile.user:
            user = obj.employee.profile.user
            full_name = f"{user.first_name} {user.last_name}".strip()
            return full_name if full_name else user.username
        return None
    
    def get_time_taken_hours(self, obj):
        """Convert minutes to hours"""
        if obj.time_taken_minutes:
            return round(obj.time_taken_minutes / 60.0, 2)
        return 0.0
    
    def get_activity_feed(self, obj):
        """Get activity feed for this task"""
        activities = ActivityLog.objects.filter(
            entity_type=ActivityLog.EntityType.TASK,
            entity_id=obj.id
        ).select_related('created_by').order_by('-created_at')
        return ActivityFeedSerializer(activities, many=True, context=self.context).data


class TaskStatisticsSerializer(serializers.Serializer):
    total_tasks = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    pending_approval = serializers.IntegerField()
    approved_tasks = serializers.IntegerField()
    total_resource_cost = serializers.DecimalField(max_digits=15, decimal_places=2, help_text="Total resource cost")


class BulkApproveSerializer(serializers.Serializer):
    task_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        min_length=1,
        help_text='List of task IDs to approve'
    )


class TaskCreateSerializer(serializers.ModelSerializer):
    estimated_time = serializers.IntegerField(source='time_taken_minutes', required=False, allow_null=True, help_text='Estimated time in minutes')
    deadline = serializers.DateField(required=False, allow_null=True, help_text='Task deadline/date (optional, informational only)')
    
    class Meta:
        model = Task
        fields = [
            'id', 'employee', 'project', 'deadline', 'task_name', 'status', 'approval_status',
            'estimated_time', 'location', 'task_description', 'internal_notes'
        ]
        read_only_fields = ['id']
    
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['created_by'] = user if user.is_authenticated else None
        
        # Remove deadline from validated_data if it's None (to avoid setting it explicitly)
        # This allows the database default/null handling to work properly
        if 'deadline' in validated_data and validated_data['deadline'] is None:
            validated_data.pop('deadline', None)
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        user = self.context['request'].user
        validated_data['updated_by'] = user if user.is_authenticated else None
        
        # Remove deadline from validated_data if it's None (to avoid setting it explicitly)
        if 'deadline' in validated_data and validated_data['deadline'] is None:
            validated_data.pop('deadline', None)
        
        return super().update(instance, validated_data)


class TaskAttachmentUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class TaskResourceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskResource
        fields = [
            'id', 'resource_name', 'quantity', 'unit_cost', 'total_cost'
        ]
        read_only_fields = ['id']
    
    def validate(self, data):
        """Calculate total_cost if not provided"""
        quantity = data.get('quantity', 0)
        unit_cost = data.get('unit_cost', 0)
        
        if 'total_cost' not in data or data['total_cost'] is None:
            data['total_cost'] = float(quantity) * float(unit_cost)
        
        return data
    
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['task'] = self.context['task']
        validated_data['created_by'] = user if user.is_authenticated else None
        return super().create(validated_data)


# Task Resources Dashboard Serializers
class TaskResourceBreakdownSerializer(serializers.ModelSerializer):
    """Serializer for resource breakdown in task resources dashboard"""
    class Meta:
        model = TaskResource
        fields = [
            'id', 'resource_name', 'quantity', 'unit_cost', 'total_cost'
        ]
        read_only_fields = ['id']


class TaskResourcesDashboardSerializer(serializers.ModelSerializer):
    """Serializer for task resources dashboard list"""
    employee_name = serializers.SerializerMethodField()
    project_name = serializers.CharField(source='project.name', read_only=True)
    tender_name = serializers.SerializerMethodField()
    resources_count = serializers.SerializerMethodField()
    grand_total = serializers.SerializerMethodField()
    resource_breakdown = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'task_name', 'employee', 'employee_name', 'project', 'project_name',
            'tender_name', 'deadline', 'resources_count', 'grand_total', 'resource_breakdown'
        ]
        read_only_fields = ['id']
    
    def get_employee_name(self, obj):
        """Get employee name from profile user"""
        if obj.employee and obj.employee.profile and obj.employee.profile.user:
            user = obj.employee.profile.user
            full_name = f"{user.first_name} {user.last_name}".strip()
            return full_name if full_name else user.username
        return None
    
    def get_tender_name(self, obj):
        """Get tender name"""
        if obj.project and obj.project.tender:
            return obj.project.tender.name
        return None
    
    def get_resources_count(self, obj):
        """Get number of resources used in this task"""
        return obj.resources.count()
    
    def get_grand_total(self, obj):
        """Get grand total of all resources in this task"""
        try:
            from django.db.models import Sum
            from django.db.models.functions import Coalesce
            from decimal import Decimal
            
            total_result = obj.resources.aggregate(
                total=Coalesce(Sum('total_cost'), 0)
            )
            total = total_result.get('total', 0) or 0
            
            # Handle Decimal type conversion
            if isinstance(total, Decimal):
                return float(total)
            elif isinstance(total, (int, float)):
                return float(total)
            else:
                return 0.0
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error calculating grand total for task {obj.id}: {str(e)}")
            return 0.0
    
    def get_resource_breakdown(self, obj):
        """Get resource breakdown for this task"""
        try:
            resources = obj.resources.all()
            return TaskResourceBreakdownSerializer(resources, many=True).data
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting resource breakdown for task {obj.id}: {str(e)}")
            return []


class TaskResourcesStatisticsSerializer(serializers.Serializer):
    """Serializer for task resources dashboard statistics"""
    total_tasks = serializers.IntegerField()
    total_resources = serializers.IntegerField()
    total_cost = serializers.DecimalField(max_digits=15, decimal_places=2)
    avg_cost_per_task = serializers.DecimalField(max_digits=15, decimal_places=2)

