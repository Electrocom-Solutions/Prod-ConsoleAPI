"""
Serializers for Notifications app.
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Notification, EmailTemplate


class NotificationListSerializer(serializers.ModelSerializer):
    """Serializer for listing notifications"""
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'type', 'type_display', 'channel', 'channel_display',
            'is_read', 'scheduled_at', 'sent_at', 'created_at', 'created_by', 'created_by_username'
        ]
        read_only_fields = ['created_at', 'sent_at', 'created_by']


class NotificationDetailSerializer(serializers.ModelSerializer):
    """Serializer for notification details"""
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'recipient_username', 'title', 'message', 'type', 'type_display',
            'channel', 'channel_display', 'is_read', 'scheduled_at', 'sent_at',
            'created_at', 'updated_at', 'created_by', 'created_by_username', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'sent_at', 'created_by', 'updated_by']


class NotificationMarkReadSerializer(serializers.Serializer):
    """Serializer for marking a notification as read"""
    pass  # No fields needed, just mark as read


class BulkMarkReadSerializer(serializers.Serializer):
    """Serializer for bulk marking notifications as read"""
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text='List of notification IDs to mark as read',
        required=False
    )
    mark_all = serializers.BooleanField(
        default=False,
        help_text='Mark all notifications as read for the current user'
    )


class NotificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating notifications (owner only - sends to all employees)"""
    scheduled_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text='Schedule notification for a specific date and time. If not set, notification is sent immediately.'
    )
    
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'type', 'channel', 'scheduled_at'
        ]
        read_only_fields = ['id']
    
    def create(self, validated_data):
        """Create notifications for all employees"""
        from django.utils import timezone
        from HR.models import Employee
        
        scheduled_at = validated_data.pop('scheduled_at', None)
        title = validated_data.get('title')
        message = validated_data.get('message')
        notification_type = validated_data.get('type')
        channel = validated_data.get('channel', Notification.Channel.IN_APP)
        
        # Get all employees (users linked to Employee model)
        employees = Employee.objects.select_related('profile', 'profile__user').all()
        
        notifications_created = []
        current_time = timezone.now()
        
        # Determine if notification should be sent immediately or scheduled
        send_immediately = scheduled_at is None or scheduled_at <= current_time
        
        for employee in employees:
            if employee.profile and employee.profile.user:
                user = employee.profile.user
                
                request_user = self.context['request'].user
                notification = Notification.objects.create(
                    recipient=user,
                    title=title,
                    message=message,
                    type=notification_type,
                    channel=channel,
                    scheduled_at=scheduled_at,
                    sent_at=current_time if send_immediately else None,
                    created_by=request_user if request_user.is_authenticated else None
                )
                
                notifications_created.append(notification)
        
        # Return the first notification (for API response)
        # In practice, you might want to return a summary
        if notifications_created:
            return notifications_created[0]
        else:
            # If no employees found, create a notification for the creator
            request_user = self.context['request'].user
            return Notification.objects.create(
                recipient=request_user if request_user.is_authenticated else None,
                title=title,
                message=message,
                type=notification_type,
                channel=channel,
                scheduled_at=scheduled_at,
                sent_at=current_time if send_immediately else None,
                created_by=request_user if request_user.is_authenticated else None
            )


# Email Template Serializers
class EmailTemplateListSerializer(serializers.ModelSerializer):
    """Serializer for listing email templates"""
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'name', 'subject', 'created_at', 'created_by', 'created_by_username'
        ]
        read_only_fields = ['created_at', 'created_by']


class EmailTemplateDetailSerializer(serializers.ModelSerializer):
    """Serializer for email template details"""
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    updated_by_username = serializers.CharField(source='updated_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'name', 'subject', 'body', 'placeholders',
            'created_at', 'updated_at', 'created_by', 'created_by_username',
            'updated_by', 'updated_by_username'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']


class EmailTemplateCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating email templates"""
    
    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'name', 'subject', 'body', 'placeholders'
        ]
        read_only_fields = ['id']
    
    def create(self, validated_data):
        """Create email template"""
        user = self.context['request'].user
        validated_data['created_by'] = user if user.is_authenticated else None
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Update email template"""
        user = self.context['request'].user
        validated_data['updated_by'] = user if user.is_authenticated else None
        return super().update(instance, validated_data)


class NotificationStatisticsSerializer(serializers.Serializer):
    """Serializer for notification statistics"""
    total_notifications = serializers.IntegerField()
    unread_count = serializers.IntegerField()
    read_count = serializers.IntegerField()


class EmailTemplateSendSerializer(serializers.Serializer):
    """Serializer for sending email using template"""
    recipients = serializers.CharField(
        required=True,
        help_text='Comma-separated email addresses (e.g., "user1@example.com, user2@example.com")'
    )
    scheduled_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text='Schedule email for a specific date and time. If not set, email is sent immediately.'
    )
    placeholder_values = serializers.DictField(
        required=False,
        allow_null=True,
        help_text='Dictionary of placeholder values to replace in the email body (e.g., {"name": "John", "date": "2025-01-01"})'
    )
    
    def validate_recipients(self, value):
        """Validate and clean recipients"""
        if not value or not value.strip():
            raise serializers.ValidationError("Recipients cannot be empty")
        
        # Split by comma and clean email addresses
        emails = [email.strip() for email in value.split(',') if email.strip()]
        
        if not emails:
            raise serializers.ValidationError("At least one valid email address is required")
        
        # Basic email validation
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        
        invalid_emails = []
        for email in emails:
            if not email_pattern.match(email):
                invalid_emails.append(email)
        
        if invalid_emails:
            raise serializers.ValidationError(f"Invalid email addresses: {', '.join(invalid_emails)}")
        
        return emails

