from django.contrib import admin
from .models import Task, TaskAttachment, TaskResource


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('task_name', 'employee', 'project', 'task_date', 'status', 'time_taken_minutes', 'created_at')
    list_filter = ('status', 'task_date', 'project', 'created_at', 'updated_at')
    search_fields = ('task_name', 'task_description', 'location', 'internal_notes', 'employee__employee_code', 'project__name')
    date_hierarchy = 'task_date'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Task Information', {
            'fields': ('employee', 'project', 'task_name', 'task_description', 'task_date', 'status')
        }),
        ('Location & Time', {
            'fields': ('location', 'time_taken_minutes')
        }),
        ('Additional Information', {
            'fields': ('internal_notes',)
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


@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ('task', 'file', 'created_at')
    list_filter = ('task', 'created_at', 'updated_at')
    search_fields = ('task__task_name', 'notes')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Attachment Information', {
            'fields': ('task', 'file', 'notes')
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


@admin.register(TaskResource)
class TaskResourceAdmin(admin.ModelAdmin):
    list_display = ('resource_name', 'task', 'quantity', 'unit_cost', 'total_cost', 'created_at')
    list_filter = ('task', 'created_at', 'updated_at')
    search_fields = ('resource_name', 'task__task_name')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Resource Information', {
            'fields': ('task', 'resource_name', 'quantity', 'unit_cost', 'total_cost')
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
