from django.contrib import admin
from .models import Employee, ContractWorker, Attendance, PayrollRecord, HolidayCalander


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_code', 'profile', 'designation', 'joining_date', 'monthly_salary', 'created_at')
    list_filter = ('designation', 'joining_date', 'created_at', 'updated_at')
    search_fields = ('employee_code', 'profile__id', 'designation')
    date_hierarchy = 'joining_date'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Employee Information', {
            'fields': ('profile', 'employee_code', 'designation', 'joining_date', 'monthly_salary')
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


@admin.register(ContractWorker)
class ContractWorkerAdmin(admin.ModelAdmin):
    list_display = ('profile', 'project', 'worker_type', 'monthly_salary', 'aadhar_no', 'department', 'created_at')
    list_filter = ('worker_type', 'department', 'project', 'created_at', 'updated_at')
    search_fields = ('profile__id', 'aadhar_no', 'uan_number', 'department', 'project__name')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Worker Information', {
            'fields': ('profile', 'project', 'worker_type', 'monthly_salary')
        }),
        ('Identification', {
            'fields': ('aadhar_no', 'uan_number', 'department')
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


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'attendance_date', 'attendance_status', 'approval_status', 'check_in_time', 'check_out_time', 'created_at')
    list_filter = ('attendance_status', 'approval_status', 'attendance_date', 'created_at', 'updated_at')
    search_fields = ('employee__employee_code', 'attendance_date', 'check_in_location', 'check_out_location', 'rejection_reason')
    date_hierarchy = 'attendance_date'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Attendance Information', {
            'fields': ('employee', 'attendance_date', 'attendance_status', 'approval_status', 'rejection_reason')
        }),
        ('Check In/Out', {
            'fields': ('check_in_time', 'check_out_time', 'check_in_location', 'check_out_location')
        }),
        ('Location Coordinates', {
            'fields': ('check_in_location_latitude', 'check_in_location_longitude', 'check_out_location_latitude', 'check_out_location_longitude'),
            'classes': ('collapse',)
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


@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
    list_display = ('employee', 'payroll_status', 'period_from', 'period_to', 'net_amount', 'payment_date', 'payment_mode', 'created_at')
    list_filter = ('payroll_status', 'payment_mode', 'period_from', 'period_to', 'payment_date', 'created_at', 'updated_at')
    search_fields = ('employee__employee_code', 'bank_transaction_reference_number', 'notes')
    date_hierarchy = 'period_from'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Payroll Information', {
            'fields': ('employee', 'payroll_status', 'period_from', 'period_to')
        }),
        ('Working Days', {
            'fields': ('working_days', 'days_present', 'net_amount')
        }),
        ('Payment Information', {
            'fields': ('payment_date', 'payment_mode', 'bank_transaction_reference_number', 'notes')
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


@admin.register(HolidayCalander)
class HolidayCalanderAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'type', 'created_at')
    list_filter = ('type', 'date', 'created_at', 'updated_at')
    search_fields = ('name', 'type')
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Holiday Information', {
            'fields': ('date', 'name', 'type')
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
