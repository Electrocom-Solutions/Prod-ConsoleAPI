from django.contrib import admin
from .models import TrainingVideo


@admin.register(TrainingVideo)
class TrainingVideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'rank', 'youtube_video_id', 'created_by', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('title', 'youtube_video_id')
    readonly_fields = ('youtube_video_id', 'created_at', 'updated_at', 'created_by', 'updated_by')
    list_editable = ('rank',)  # Allow editing rank directly from list view
    
    fieldsets = (
        ('Video Information', {
            'fields': ('title', 'youtube_url', 'youtube_video_id', 'rank')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_by', 'updated_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
            obj.created_by = request.user
        else:  # If updating existing object
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)
