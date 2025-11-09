from django.contrib import admin
from .models import Stock


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit_of_measure', 'quantity', 'price', 'created_at')
    list_filter = ('unit_of_measure', 'created_at', 'updated_at')
    search_fields = ('name', 'description', 'unit_of_measure')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Stock Information', {
            'fields': ('name', 'description', 'unit_of_measure', 'quantity', 'price')
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
