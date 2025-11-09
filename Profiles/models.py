from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="profiles")
    photo = models.ImageField(upload_to="profiles/photos/", blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pin_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    aadhar_number = models.CharField(max_length=20, blank=True, null=True)
    pan_number = models.CharField(max_length=20, blank=True, null=True)
    aadhar_card = models.FileField(upload_to="profiles/docs/", blank=True, null=True)
    pan_card = models.FileField(upload_to="profiles/docs/", blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="profiles_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="profiles_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile {self.id}"


class Email(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="emails")
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)
    is_primary = models.BooleanField(default=False)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="emails_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="emails_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email


class MobileNumber(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mobile_numbers")
    mobile_number = models.CharField(max_length=20, unique=True)
    is_verified = models.BooleanField(default=False)
    is_primary = models.BooleanField(default=False)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="mobiles_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="mobiles_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.mobile_number


class OTP(models.Model):
    class OTPType(models.TextChoices):
        E = "E", "E"
        M = "M", "M"

    class OTPFor(models.TextChoices):
        REGISTRATION = "Registration", "Registration"
        RESET = "Reset", "Reset"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")
    otp = models.CharField(max_length=10)
    otp_type = models.CharField(max_length=1, choices=OTPType.choices)
    otp_for = models.CharField(max_length=20, choices=OTPFor.choices)
    is_verified = models.BooleanField(default=False)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="otps_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="otps_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"OTP {self.id} for {self.user_id}"

