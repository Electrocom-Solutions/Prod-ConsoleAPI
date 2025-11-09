from django.db import models
from django.contrib.auth.models import User


class AMC(models.Model):
    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        ACTIVE = "Active", "Active"
        EXPIRED = "Expired", "Expired"
        CANCELED = "Canceled", "Canceled"

    class BillingCycle(models.TextChoices):
        MONTHLY = "Monthly", "Monthly"
        QUARTERLY = "Quarterly", "Quarterly"
        HALF_YEARLY = "Half-yearly", "Half-yearly"
        YEARLY = "Yearly", "Yearly"

    client = models.ForeignKey("Clients.Client", on_delete=models.CASCADE, related_name="amcs")
    amc_number = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    billing_cycle = models.CharField(max_length=20, choices=BillingCycle.choices)
    notes = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="amc_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="amc_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"AMC {self.amc_number}"


class AMCBilling(models.Model):
    class PaymentMode(models.TextChoices):
        CASH = "Cash", "Cash"
        CHEQUE = "Cheque", "Cheque"
        BANK_TRANSFER = "Bank Transfer", "Bank Transfer"
        UPI = "UPI", "UPI"

    amc = models.ForeignKey(AMC, on_delete=models.CASCADE, related_name="billings")
    bill_number = models.CharField(max_length=100)
    bill_date = models.DateField()
    period_from = models.DateField()
    period_to = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid = models.BooleanField(default=False)
    payment_date = models.DateField(blank=True, null=True)
    payment_mode = models.CharField(max_length=20, choices=PaymentMode.choices, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="amcbilling_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="amcbilling_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Bill {self.bill_number} - AMC {self.amc.amc_number}"

