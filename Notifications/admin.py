from django.contrib import admin
from .models import Notification, EmailTemplate, DeviceToken


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'type', 'channel', 'is_read', 'created_at')
    list_filter = ('type', 'channel', 'is_read', 'created_at', 'updated_at')
    search_fields = ('title', 'message', 'recipient__username', 'recipient__email')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Notification Information', {
            'fields': ('recipient', 'title', 'message', 'type', 'channel', 'is_read')
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_by', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        from django.utils import timezone
        from .utils import send_fcm_push_notification
        import logging
        
        logger = logging.getLogger(__name__)
        
        if not change:
            obj.created_by = request.user
            # Set sent_at if not already set (for immediate notifications)
            if not obj.sent_at and (not obj.scheduled_at or obj.scheduled_at <= timezone.now()):
                obj.sent_at = timezone.now()
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        
        # Send FCM push notification if notification is sent and channel supports it
        if obj.sent_at and (obj.channel == Notification.Channel.IN_APP or obj.channel == Notification.Channel.PUSH):
            try:
                send_fcm_push_notification(
                    user=obj.recipient,
                    title=obj.title,
                    message=obj.message,
                    notification_type=obj.type,
                    notification_id=obj.id
                )
                logger.info(f"FCM push notification sent for notification {obj.id} to user {obj.recipient.username}")
            except Exception as e:
                logger.error(f"Failed to send FCM push notification for notification {obj.id}: {str(e)}")


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('name', 'subject', 'body', 'placeholders')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'subject', 'body', 'placeholders')
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_by', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_type', 'is_active', 'created_at', 'updated_at')
    list_filter = ('device_type', 'is_active', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email', 'token', 'device_id')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'token_preview')
    fieldsets = (
        ('Device Information', {
            'fields': ('user', 'token', 'token_preview', 'device_type', 'device_id', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def token_preview(self, obj):
        """Show truncated token for display"""
        if obj.token:
            return f"{obj.token[:50]}..." if len(obj.token) > 50 else obj.token
        return "-"
    token_preview.short_description = "Token Preview"
