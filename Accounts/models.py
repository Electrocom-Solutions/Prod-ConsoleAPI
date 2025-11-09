from django.db import models
from django.contrib.auth.models import User


class PaymentTracker(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING = "Pending", "Pending"
        PAID = "Paid", "Paid"

    class PaymentMode(models.TextChoices):
        CASH = "Cash", "Cash"
        CHEQUE = "Cheque", "Cheque"
        BANK_TRANSFER = "Bank Transfer", "Bank Transfer"
        UPI = "UPI", "UPI"

    worker_name = models.CharField(max_length=255)
    mobile_number = models.CharField(max_length=20)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2)
    place_of_work = models.CharField(max_length=255)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    account_number = models.CharField(max_length=64, blank=True, null=True)
    ifsc_code = models.CharField(max_length=32, blank=True, null=True)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    payment_date = models.DateField(blank=True, null=True)
    payment_mode = models.CharField(max_length=20, choices=PaymentMode.choices, blank=True, null=True)
    sheet_attachment = models.FileField(upload_to="accounts/payment_sheets/", blank=True, null=True)
    sheet_period = models.DateField(help_text="Use first day of the month to represent the period")

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="paymenttrackers_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="paymenttrackers_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.worker_name} - {self.sheet_period.strftime('%b %Y') if self.sheet_period else ''}"


class BankAccount(models.Model):
    profile = models.ForeignKey("Profiles.Profile", on_delete=models.CASCADE, related_name="bank_accounts")
    bank_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=64)
    ifsc_code = models.CharField(max_length=32)
    branch = models.CharField(max_length=255, blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="bankaccounts_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="bankaccounts_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"

