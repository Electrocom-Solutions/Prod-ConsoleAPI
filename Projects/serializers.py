from rest_framework import serializers
from .models import Project


class ProjectListSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    tender_name = serializers.CharField(source='tender.name', read_only=True, allow_null=True)
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'client', 'client_name', 'tender', 'tender_name',
            'start_date', 'end_date', 'status', 'created_at'
        ]
        read_only_fields = ['created_at']


class ProjectStatisticsSerializer(serializers.Serializer):
    total_projects = serializers.IntegerField()
    planned_projects = serializers.IntegerField()
    in_progress_projects = serializers.IntegerField()
    completed_projects = serializers.IntegerField()
    on_hold_projects = serializers.IntegerField()
    canceled_projects = serializers.IntegerField()


class ProjectDetailSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    tender_name = serializers.CharField(source='tender.name', read_only=True, allow_null=True)
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'client', 'client_name', 'tender', 'tender_name',
            'start_date', 'end_date', 'status', 'created_at', 'updated_at',
            'created_by', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']


class ProjectCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'client', 'tender',
            'start_date', 'end_date', 'status'
        ]
        read_only_fields = ['id']
    
    def validate(self, data):
        """Validate that end_date is not before start_date"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError("End date cannot be before start date.")
        
        return data
    
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['created_by'] = user if user.is_authenticated else None
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        user = self.context['request'].user
        validated_data['updated_by'] = user if user.is_authenticated else None
        return super().update(instance, validated_data)

