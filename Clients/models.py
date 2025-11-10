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
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    photo = models.ImageField(upload_to="clients/photos/", blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=20, choices=Gender.choices, blank=True, null=True)
    aadhar_number = models.CharField(max_length=20, blank=True, null=True)
    pan_number = models.CharField(max_length=20, blank=True, null=True)
    primary_contact_name = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="clients_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="clients_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        """Return client name from profile.user"""
        if self.profile and self.profile.user:
            first_name = self.profile.user.first_name or ""
            last_name = self.profile.user.last_name or ""
            full_name = f"{first_name} {last_name}".strip()
            if full_name:
                return full_name
            # Fallback to username if name is empty
            if self.profile.user.username:
                return self.profile.user.username
        return f"Client {self.id}"
    
    @property
    def full_name(self):
        """Return full name from profile.user"""
        if self.profile and self.profile.user:
            first_name = self.profile.user.first_name or ""
            last_name = self.profile.user.last_name or ""
            full_name = f"{first_name} {last_name}".strip()
            if full_name:
                return full_name
            # Fallback to username if name is empty
            if self.profile.user.username:
                return self.profile.user.username
        return ""


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

