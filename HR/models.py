from django.db import models
from django.contrib.auth.models import User


class Employee(models.Model):
    class Designation(models.TextChoices):
        TECHNICIAN = "Technician", "Technician"
        FIELD_STAFF = "Field Staff", "Field Staff"
        COMPUTER_OPERATOR = "Computer Operator", "Computer Operator"
        OTHER = "Other", "Other"

    profile = models.ForeignKey("Profiles.Profile", on_delete=models.CASCADE, related_name="employees")
    employee_code = models.CharField(max_length=50, unique=True)
    designation = models.CharField(max_length=30, choices=Designation.choices)
    joining_date = models.DateField()
    monthly_salary = models.DecimalField(max_digits=12, decimal_places=2)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="employees_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="employees_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee_code}"


class ContractWorker(models.Model):
    class WorkerType(models.TextChoices):
        UNSKILLED = "Unskilled", "Unskilled"
        SEMI_SKILLED = "Semi-Skilled", "Semi-Skilled"
        SKILLED = "Skilled", "Skilled"

    profile = models.ForeignKey("Profiles.Profile", on_delete=models.CASCADE, related_name="contract_workers")
    project = models.ForeignKey("Projects.Project", on_delete=models.SET_NULL, related_name="contract_workers", blank=True, null=True)
    worker_type = models.CharField(max_length=20, choices=WorkerType.choices)
    monthly_salary = models.DecimalField(max_digits=12, decimal_places=2)
    aadhar_no = models.CharField(max_length=20)
    uan_number = models.CharField(max_length=20, blank=True, null=True)
    esi = models.CharField(max_length=50, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="contractworkers_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="contractworkers_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ContractWorker {self.id}"


class Attendance(models.Model):
    class AttendanceStatus(models.TextChoices):
        PRESENT = "Present", "Present"
        ABSENT = "Absent", "Absent"
        HALF_DAY = "Half-Day", "Half-Day"
        LEAVE = "Leave", "Leave"

    class ApprovalStatus(models.TextChoices):
        APPROVED = "Approved", "Approved"
        PENDING = "Pending", "Pending"
        REJECTED = "Rejected", "Rejected"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="attendance_records")
    attendance_date = models.DateField()
    attendance_status = models.CharField(max_length=20, choices=AttendanceStatus.choices)
    approval_status = models.CharField(max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING)
    rejection_reason = models.TextField(blank=True, null=True)
    check_in_time = models.DateTimeField(blank=True, null=True)
    check_out_time = models.DateTimeField(blank=True, null=True)
    check_in_location = models.CharField(max_length=255, blank=True, null=True)
    check_out_location = models.CharField(max_length=255, blank=True, null=True)
    check_in_location_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    check_in_location_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    check_out_location_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    check_out_location_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    check_in_selfie = models.ImageField(upload_to="attendance/check_in_selfies/", blank=True, null=True)
    check_out_selfie = models.ImageField(upload_to="attendance/check_out_selfies/", blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="attendance_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="attendance_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("employee", "attendance_date")

    def __str__(self):
        return f"{self.employee} - {self.attendance_date}"


class PayrollRecord(models.Model):
    class PayrollStatus(models.TextChoices):
        PAID = "Paid", "Paid"
        PENDING = "Pending", "Pending"

    class PaymentMode(models.TextChoices):
        CASH = "Cash", "Cash"
        BANK_TRANSFER = "Bank Transfer", "Bank Transfer"
        CHEQUE = "Cheque", "Cheque"
        UPI = "UPI", "UPI"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="payroll_records")
    payroll_status = models.CharField(max_length=20, choices=PayrollStatus.choices, default=PayrollStatus.PENDING)
    period_from = models.DateField()
    period_to = models.DateField()
    working_days = models.PositiveSmallIntegerField()
    days_present = models.PositiveSmallIntegerField()
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField(blank=True, null=True)
    payment_mode = models.CharField(max_length=20, choices=PaymentMode.choices, blank=True, null=True)
    bank_transaction_reference_number = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="payroll_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="payroll_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payroll {self.id} - {self.employee}"


class HolidayCalander(models.Model):
    class HolidayType(models.TextChoices):
        NATIONAL = "National", "National"
        FESTIVAL = "Festival", "Festival"
        COMPANY = "Company", "Company"

    date = models.DateField(unique=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=HolidayType.choices)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="holidays_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="holidays_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.date})"

