from django.contrib import admin
from .models import Profile, Email, MobileNumber, OTP


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'date_of_birth', 'gender', 'city', 'state', 'country', 'created_at')
    list_filter = ('gender', 'city', 'state', 'country', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email', 'city', 'state', 'pin_code', 'country')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Profile Information', {
            'fields': ('user', 'photo', 'date_of_birth', 'gender')
        }),
        ('Address Information', {
            'fields': ('address', 'city', 'state', 'pin_code', 'country')
        }),
        ('Identity Documents', {
            'fields': ('aadhar_number', 'pan_number', 'aadhar_card', 'pan_card')
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


@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    list_display = ('email', 'user', 'is_verified', 'is_primary', 'created_at')
    list_filter = ('is_verified', 'is_primary', 'created_at', 'updated_at')
    search_fields = ('email', 'user__username')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Email Information', {
            'fields': ('user', 'email', 'is_verified', 'is_primary')
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


@admin.register(MobileNumber)
class MobileNumberAdmin(admin.ModelAdmin):
    list_display = ('mobile_number', 'user', 'is_verified', 'is_primary', 'created_at')
    list_filter = ('is_verified', 'is_primary', 'created_at', 'updated_at')
    search_fields = ('mobile_number', 'user__username')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Mobile Number Information', {
            'fields': ('user', 'mobile_number', 'is_verified', 'is_primary')
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


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ('user', 'otp', 'otp_type', 'otp_for', 'is_verified', 'created_at')
    list_filter = ('otp_type', 'otp_for', 'is_verified', 'created_at', 'updated_at')
    search_fields = ('user__username', 'otp')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('OTP Information', {
            'fields': ('user', 'otp', 'otp_type', 'otp_for', 'is_verified')
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
