from django.contrib import admin
from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'tender', 'status', 'start_date', 'end_date', 'created_at')
    list_filter = ('status', 'start_date', 'end_date', 'created_at', 'updated_at')
    search_fields = ('name', 'description', 'tender__name')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Project Information', {
            'fields': ('tender', 'name', 'description', 'status')
        }),
        ('Date Information', {
            'fields': ('start_date', 'end_date')
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
