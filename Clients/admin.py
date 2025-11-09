from django.contrib import admin
from .models import Client, Firm


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'profile', 'primary_contact_name', 'first_name', 'last_name', 'email', 'phone_number', 'created_at')
    list_filter = ('designation', 'gender', 'created_at', 'updated_at')
    search_fields = ('name', 'first_name', 'last_name', 'primary_contact_name', 'email', 'phone_number', 'notes')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Client Information', {
            'fields': ('profile', 'first_name', 'last_name', 'name', 'primary_contact_name', 'email', 'phone_number')
        }),
        ('Personal Information', {
            'fields': ('photo', 'date_of_birth', 'gender', 'aadhar_number', 'pan_number')
        }),
        ('Professional Information', {
            'fields': ('designation', 'joining_date', 'monthly_salary')
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


@admin.register(Firm)
class FirmAdmin(admin.ModelAdmin):
    list_display = ('firm_name', 'firm_type', 'firm_owner_profile', 'official_email', 'gst_number', 'pan_number', 'created_at')
    list_filter = ('firm_type', 'created_at', 'updated_at')
    search_fields = ('firm_name', 'gst_number', 'pan_number', 'address', 'official_email', 'official_mobile_number')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Firm Information', {
            'fields': ('firm_name', 'firm_type', 'firm_owner_profile')
        }),
        ('Contact Information', {
            'fields': ('official_email', 'official_mobile_number', 'address')
        }),
        ('Registration Details', {
            'fields': ('gst_number', 'pan_number')
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
