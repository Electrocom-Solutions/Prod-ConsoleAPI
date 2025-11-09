from django.contrib import admin
from .models import PaymentTracker, BankAccount


@admin.register(PaymentTracker)
class PaymentTrackerAdmin(admin.ModelAdmin):
    list_display = ('worker_name', 'mobile_number', 'net_salary', 'payment_status', 'payment_date', 'sheet_period', 'created_at')
    list_filter = ('payment_status', 'payment_mode', 'sheet_period', 'created_at', 'updated_at')
    search_fields = ('worker_name', 'mobile_number', 'place_of_work', 'bank_name', 'account_number', 'ifsc_code')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Worker Information', {
            'fields': ('worker_name', 'mobile_number', 'place_of_work')
        }),
        ('Payment Details', {
            'fields': ('net_salary', 'payment_status', 'payment_date', 'payment_mode')
        }),
        ('Bank Information', {
            'fields': ('bank_name', 'account_number', 'ifsc_code')
        }),
        ('Sheet Information', {
            'fields': ('sheet_period', 'sheet_attachment')
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


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('profile', 'bank_name', 'account_number', 'ifsc_code', 'branch', 'created_at')
    list_filter = ('bank_name', 'created_at', 'updated_at')
    search_fields = ('profile__id', 'bank_name', 'account_number', 'ifsc_code', 'branch')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Account Information', {
            'fields': ('profile', 'bank_name', 'account_number', 'ifsc_code', 'branch')
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
