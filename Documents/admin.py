from django.contrib import admin
from .models import DocumentTemplate, DocumentTemplateVersion, CombinedDocument


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ('title', 'firm', 'category', 'created_at')
    list_filter = ('category', 'firm', 'created_at', 'updated_at')
    search_fields = ('title', 'category', 'description', 'firm__firm_name')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Template Information', {
            'fields': ('firm', 'title', 'category', 'description')
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


@admin.register(DocumentTemplateVersion)
class DocumentTemplateVersionAdmin(admin.ModelAdmin):
    list_display = ('template', 'version_number', 'file_type', 'is_published', 'created_at')
    list_filter = ('file_type', 'is_published', 'template', 'created_at', 'updated_at')
    search_fields = ('template__title', 'version_number')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Version Information', {
            'fields': ('template', 'version_number', 'file', 'file_type', 'is_published')
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


@admin.register(CombinedDocument)
class CombinedDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'template', 'created_at')
    list_filter = ('template', 'created_at', 'updated_at')
    search_fields = ('title', 'template__title')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Document Information', {
            'fields': ('template', 'title')
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
