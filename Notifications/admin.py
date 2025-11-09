from django.contrib import admin
from .models import Notification, EmailTemplate


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
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


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
