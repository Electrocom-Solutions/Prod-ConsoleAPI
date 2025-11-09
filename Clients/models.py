from django.db import models
from django.contrib.auth.models import User


class Client(models.Model):
    class Gender(models.TextChoices):
        MALE = "Male", "Male"
        FEMALE = "Female", "Female"
    
    class Designation(models.TextChoices):
        TECHNICIAN = "Technician", "Technician"
        FIELD_STAFF = "Field Staff", "Field Staff"
        COMPUTER_OPERATOR = "Computer Operator", "Computer Operator"
    
    profile = models.ForeignKey("Profiles.Profile", on_delete=models.CASCADE, related_name="clients")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    photo = models.ImageField(upload_to="clients/photos/", blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=20, choices=Gender.choices, blank=True, null=True)
    aadhar_number = models.CharField(max_length=20, blank=True, null=True)
    pan_number = models.CharField(max_length=20, blank=True, null=True)
    designation = models.CharField(max_length=50, choices=Designation.choices, blank=True, null=True)
    joining_date = models.DateField(blank=True, null=True)
    monthly_salary = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    
    # Legacy fields for backward compatibility
    name = models.CharField(max_length=255, blank=True, null=True)
    primary_contact_name = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="clients_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="clients_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.name or f"Client {self.id}"
    
    @property
    def full_name(self):
        """Return full name"""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.name or ""


class Firm(models.Model):
    class FirmType(models.TextChoices):
        PROPRIETORSHIP = "Proprietorship", "Proprietorship"
        PARTNERSHIP = "Partnership", "Partnership"
        PVT_LTD = "Pvt Ltd", "Pvt Ltd"
        LLP = "LLP", "LLP"
    
    firm_name = models.CharField(max_length=255)
    firm_type = models.CharField(max_length=20, choices=FirmType.choices, blank=True, null=True)
    firm_owner_profile = models.ForeignKey("Profiles.Profile", on_delete=models.SET_NULL, related_name="firms_owned", blank=True, null=True)
    official_email = models.EmailField(blank=True, null=True)
    official_mobile_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    gst_number = models.CharField(max_length=50, blank=True, null=True)
    pan_number = models.CharField(max_length=50, blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="firms_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="firms_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.firm_name

