from django.db import models
from django.contrib.auth.models import User


class Tender(models.Model):
    class Status(models.TextChoices):
        DRAFT = "Draft", "Draft"
        FILED = "Filed", "Filed"
        AWARDED = "Awarded", "Awarded"
        LOST = "Lost", "Lost"
        CLOSED = "Closed", "Closed"

    name = models.CharField(max_length=255)
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    filed_date = models.DateField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    estimated_value = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.FILED)
    emd_collected = models.BooleanField(default=False, help_text="Whether EMD has been collected for this tender")
    emd_collected_date = models.DateField(blank=True, null=True, help_text="Date when EMD was collected")
    emd_collected_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="tenders_emd_collected", blank=True, null=True, help_text="User who marked EMD as collected")

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="tenders_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="tenders_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class TenderDeposit(models.Model):
    class DepositType(models.TextChoices):
        EMD_SECURITY1 = "EMD_Security1", "EMD_Security1"
        EMD_SECURITY2 = "EMD_Security2", "EMD_Security2"

    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name="deposits")
    dd_date = models.DateField()
    dd_number = models.CharField(max_length=100)
    dd_amount = models.DecimalField(max_digits=12, decimal_places=2)
    dd_beneficiary_name = models.CharField(max_length=255)
    bank_name = models.CharField(max_length=255)
    deposit_type = models.CharField(max_length=20, choices=DepositType.choices)
    is_refunded = models.BooleanField(default=False)
    refund_date = models.DateField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="tenderdeposits_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="tenderdeposits_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Deposit {self.dd_number}"


class TenderDocument(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to="tenders/documents/")

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="tenderdocuments_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="tenderdocuments_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"TenderDocument {self.id}"

