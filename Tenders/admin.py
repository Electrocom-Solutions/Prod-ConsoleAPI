from django.contrib import admin
from .models import Tender, TenderDeposit, TenderDocument


@admin.register(Tender)
class TenderAdmin(admin.ModelAdmin):
    list_display = ('name', 'reference_number', 'status', 'filed_date', 'start_date', 'end_date', 'estimated_value', 'created_at')
    list_filter = ('status', 'filed_date', 'start_date', 'end_date', 'created_at', 'updated_at')
    search_fields = ('name', 'reference_number', 'description')
    date_hierarchy = 'filed_date'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Tender Information', {
            'fields': ('name', 'reference_number', 'description', 'status')
        }),
        ('Date Information', {
            'fields': ('filed_date', 'start_date', 'end_date')
        }),
        ('Financial Information', {
            'fields': ('estimated_value',)
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


@admin.register(TenderDeposit)
class TenderDepositAdmin(admin.ModelAdmin):
    list_display = ('tender', 'deposit_type', 'dd_number', 'dd_amount', 'dd_date', 'is_refunded', 'refund_date', 'created_at')
    list_filter = ('deposit_type', 'is_refunded', 'dd_date', 'refund_date', 'created_at', 'updated_at')
    search_fields = ('tender__name', 'dd_number', 'dd_beneficiary_name', 'bank_name')
    date_hierarchy = 'dd_date'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Deposit Information', {
            'fields': ('tender', 'deposit_type', 'dd_date', 'dd_number', 'dd_amount', 'dd_beneficiary_name', 'bank_name')
        }),
        ('Refund Information', {
            'fields': ('is_refunded', 'refund_date')
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


@admin.register(TenderDocument)
class TenderDocumentAdmin(admin.ModelAdmin):
    list_display = ('tender', 'file', 'created_at')
    list_filter = ('tender', 'created_at', 'updated_at')
    search_fields = ('tender__name', 'tender__reference_number')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Document Information', {
            'fields': ('tender', 'file')
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
