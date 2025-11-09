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

