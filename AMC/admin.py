from django.contrib import admin
from .models import AMC, AMCBilling


@admin.register(AMC)
class AMCAdmin(admin.ModelAdmin):
    list_display = ('amc_number', 'client', 'amount', 'status', 'billing_cycle', 'start_date', 'end_date', 'created_at')
    list_filter = ('status', 'billing_cycle', 'start_date', 'end_date', 'created_at', 'updated_at')
    search_fields = ('amc_number', 'client__name', 'notes')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('AMC Information', {
            'fields': ('amc_number', 'client', 'amount', 'status', 'billing_cycle')
        }),
        ('Date Information', {
            'fields': ('start_date', 'end_date')
        }),
        ('Additional Information', {
            'fields': ('notes',)
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


@admin.register(AMCBilling)
class AMCBillingAdmin(admin.ModelAdmin):
    list_display = ('bill_number', 'amc', 'bill_date', 'amount', 'paid', 'payment_date', 'payment_mode', 'period_from', 'period_to')
    list_filter = ('paid', 'payment_mode', 'bill_date', 'payment_date', 'created_at', 'updated_at')
    search_fields = ('bill_number', 'amc__amc_number', 'notes')
    date_hierarchy = 'bill_date'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Billing Information', {
            'fields': ('amc', 'bill_number', 'bill_date', 'amount', 'period_from', 'period_to')
        }),
        ('Payment Information', {
            'fields': ('paid', 'payment_date', 'payment_mode')
        }),
        ('Additional Information', {
            'fields': ('notes',)
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
