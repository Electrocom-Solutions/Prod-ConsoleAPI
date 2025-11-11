"""
Serializers for Notifications app.
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Notification, EmailTemplate


class NotificationListSerializer(serializers.ModelSerializer):
    """Serializer for listing notifications"""
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)
    recipient_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'type', 'type_display', 'channel', 'channel_display',
            'is_read', 'scheduled_at', 'sent_at', 'created_at', 'created_by', 'created_by_username',
            'recipient', 'recipient_username', 'recipient_count'
        ]
        read_only_fields = ['created_at', 'sent_at', 'created_by']
    
    def get_recipient_count(self, obj):
        """Get count of recipients for scheduled notifications (grouped by title, message, scheduled_at, created_by)"""
        # Only calculate for scheduled notifications (not yet sent)
        if obj.scheduled_at and not obj.sent_at:
            from .models import Notification
            count = Notification.objects.filter(
                title=obj.title,
                message=obj.message,
                scheduled_at=obj.scheduled_at,
                created_by=obj.created_by,
                sent_at__isnull=True
            ).count()
            return count
        return None


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
        from Scheduler.tasks import send_scheduled_notification
        from .utils import send_fcm_push_notification
        import logging
        
        logger = logging.getLogger(__name__)
        
        scheduled_at = validated_data.pop('scheduled_at', None)
        title = validated_data.get('title')
        message = validated_data.get('message')
        notification_type = validated_data.get('type')
        channel = validated_data.get('channel', Notification.Channel.IN_APP)
        
        current_time = timezone.now()
        request_user = self.context['request'].user
        
        # Determine if notification should be sent immediately or scheduled
        send_immediately = scheduled_at is None or scheduled_at <= current_time
        
        if send_immediately:
            # Send immediately - create notifications for all employees now
            employees = Employee.objects.select_related('profile', 'profile__user').all()
            notifications_created = []
            
            for employee in employees:
                if employee.profile and employee.profile.user:
                    user = employee.profile.user
                    notification = Notification.objects.create(
                        recipient=user,
                        title=title,
                        message=message,
                        type=notification_type,
                        channel=channel,
                        scheduled_at=None,
                        sent_at=current_time,
                        created_by=request_user if request_user.is_authenticated else None
                    )
                    notifications_created.append(notification)
                    
                    # Send FCM push notification if channel includes Push or In-App
                    if channel == Notification.Channel.PUSH or channel == Notification.Channel.IN_APP:
                        send_fcm_push_notification(
                            user=user,
                            title=title,
                            message=message,
                            notification_type=notification_type,
                            notification_id=notification.id
                        )
            
            # Return the first notification (for API response)
            if notifications_created:
                return notifications_created[0]
            else:
                # If no employees found, create a notification for the creator
                notification = Notification.objects.create(
                    recipient=request_user if request_user.is_authenticated else None,
                    title=title,
                    message=message,
                    type=notification_type,
                    channel=channel,
                    scheduled_at=None,
                    sent_at=current_time,
                    created_by=request_user if request_user.is_authenticated else None
                )
                
                # Send FCM push notification if channel includes Push or In-App
                if channel == Notification.Channel.PUSH or channel == Notification.Channel.IN_APP:
                    send_fcm_push_notification(
                        user=request_user,
                        title=title,
                        message=message,
                        notification_type=notification_type,
                        notification_id=notification.id
                    )
                
                return notification
        else:
            # Schedule for later - create a Celery task scheduled for the specific time
            logger.info(f"Scheduling notification for {scheduled_at} (type: {type(scheduled_at)})")
            
            # Ensure scheduled_at is timezone-aware and in UTC for Celery
            import pytz
            from django.conf import settings
            
            # If scheduled_at is timezone-naive, assume it's in Asia/Kolkata timezone
            if timezone.is_naive(scheduled_at):
                kolkata_tz = pytz.timezone('Asia/Kolkata')
                scheduled_at = kolkata_tz.localize(scheduled_at)
                logger.info(f"Converted timezone-naive datetime to Asia/Kolkata: {scheduled_at}")
            
            # Convert to UTC for Celery (Celery uses UTC internally)
            scheduled_at_utc = scheduled_at.astimezone(pytz.UTC)
            logger.info(f"Scheduled time in UTC: {scheduled_at_utc}")
            
            # Verify the scheduled time is in the future
            if scheduled_at_utc <= timezone.now():
                logger.warning(f"Scheduled time {scheduled_at_utc} is not in the future. Sending immediately.")
                # Fall back to immediate sending
                employees = Employee.objects.select_related('profile', 'profile__user').all()
                notifications_created = []
                
                for employee in employees:
                    if employee.profile and employee.profile.user:
                        user = employee.profile.user
                        notification = Notification.objects.create(
                            recipient=user,
                            title=title,
                            message=message,
                            type=notification_type,
                            channel=channel,
                            scheduled_at=None,
                            sent_at=current_time,
                            created_by=request_user if request_user.is_authenticated else None
                        )
                        notifications_created.append(notification)
                
                if notifications_created:
                    return notifications_created[0]
                else:
                    return Notification.objects.create(
                        recipient=request_user if request_user.is_authenticated else None,
                        title=title,
                        message=message,
                        type=notification_type,
                        channel=channel,
                        scheduled_at=None,
                        sent_at=current_time,
                        created_by=request_user if request_user.is_authenticated else None
                    )
            
            # Schedule the task to create notifications at the scheduled time
            try:
                task_result = send_scheduled_notification.apply_async(
                    args=[title, message, notification_type, channel],
                    kwargs={'created_by_id': request_user.id if request_user.is_authenticated else None},
                    eta=scheduled_at_utc  # Use UTC time for Celery
                )
                
                logger.info(f"Notification scheduled successfully for {scheduled_at} (UTC: {scheduled_at_utc}) with task ID: {task_result.id}")
            except Exception as e:
                logger.error(f"Error scheduling notification task: {str(e)}", exc_info=True)
                raise serializers.ValidationError(f"Failed to schedule notification: {str(e)}")
            
            # Create scheduled notifications for all employees NOW (so they can be viewed)
            # These will be marked as sent when the Celery task runs
            employees = Employee.objects.select_related('profile', 'profile__user').all()
            notifications_created = []
            
            for employee in employees:
                if employee.profile and employee.profile.user:
                    user = employee.profile.user
                    notification = Notification.objects.create(
                        recipient=user,
                        title=title,
                        message=message,
                        type=notification_type,
                        channel=channel,
                        scheduled_at=scheduled_at,  # Store original timezone-aware datetime
                        sent_at=None,  # Not sent yet - will be set when Celery task runs
                        created_by=request_user if request_user.is_authenticated else None
                    )
                    notifications_created.append(notification)
            
            # Return the first notification (for API response)
            if notifications_created:
                return notifications_created[0]
            else:
                # If no employees found, create a notification for the creator
                return Notification.objects.create(
                    recipient=request_user if request_user.is_authenticated else None,
                    title=title,
                    message=message,
                    type=notification_type,
                    channel=channel,
                    scheduled_at=scheduled_at,  # Store original timezone-aware datetime
                    sent_at=None,  # Not sent yet - will be set when Celery task runs
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

