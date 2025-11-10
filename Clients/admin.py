from django.contrib import admin
from .models import Client, Firm


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'profile', 'primary_contact_name', 'get_email', 'phone_number', 'created_at')
    list_filter = ('gender', 'created_at', 'updated_at')
    search_fields = ('profile__user__first_name', 'profile__user__last_name', 'profile__user__email', 'primary_contact_name', 'phone_number', 'notes')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by', 'get_full_name', 'get_email')
    fieldsets = (
        ('Client Information', {
            'fields': ('profile', 'primary_contact_name', 'phone_number')
        }),
        ('Personal Information', {
            'fields': ('photo', 'date_of_birth', 'gender', 'aadhar_number', 'pan_number')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_by', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_full_name(self, obj):
        """Get full name from profile.user - uses the model's full_name property"""
        return obj.full_name
    get_full_name.short_description = 'Name'
    
    def get_email(self, obj):
        """Get email from profile.user"""
        if obj.profile and obj.profile.user:
            return obj.profile.user.email or ""
        return ""
    get_email.short_description = 'Email'

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
