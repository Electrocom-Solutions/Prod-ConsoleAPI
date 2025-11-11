from django.db import models
from django.contrib.auth.models import User


class Notification(models.Model):
    class Type(models.TextChoices):
        TASK = "Task", "Task"
        AMC = "AMC", "AMC"
        TENDER = "Tender", "Tender"
        PAYROLL = "Payroll", "Payroll"
        SYSTEM = "System", "System"
        OTHER = "Other", "Other"

    class Channel(models.TextChoices):
        IN_APP = "In-App", "In-App"
        EMAIL = "Email", "Email"
        PUSH = "Push", "Push"

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=255)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=Type.choices)
    channel = models.CharField(max_length=20, choices=Channel.choices)
    is_read = models.BooleanField(default=False)
    scheduled_at = models.DateTimeField(blank=True, null=True, help_text="Schedule notification for a specific date and time. If not set, notification is sent immediately.")
    sent_at = models.DateTimeField(blank=True, null=True, help_text="When the notification was actually sent")

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="notifications_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="notifications_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class EmailTemplate(models.Model):
    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    placeholders = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="emailtemplates_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="emailtemplates_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class DeviceToken(models.Model):
    """
    Store FCM device tokens for push notifications
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="device_tokens")
    token = models.CharField(max_length=255, unique=True, help_text="FCM device token")
    device_type = models.CharField(max_length=20, choices=[('android', 'Android'), ('ios', 'iOS')], blank=True, null=True)
    device_id = models.CharField(max_length=255, blank=True, null=True, help_text="Unique device identifier")
    is_active = models.BooleanField(default=True, help_text="Whether this token is still valid")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'token')

    def __str__(self):
        return f"{self.user.username} - {self.device_type or 'Unknown'}"

