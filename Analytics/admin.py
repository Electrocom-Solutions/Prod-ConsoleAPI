from django.contrib import admin
from .models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('entity_type', 'entity_id', 'action', 'created_by', 'created_at')
    list_filter = ('entity_type', 'action', 'created_at', 'updated_at')
    search_fields = ('entity_type', 'entity_id', 'description', 'created_by__username')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Activity Information', {
            'fields': ('entity_type', 'entity_id', 'action', 'description')
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
