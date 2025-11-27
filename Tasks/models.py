from django.db import models
from django.contrib.auth.models import User


class Task(models.Model):
    class Status(models.TextChoices):
        DRAFT = "Draft", "Draft"
        IN_PROGRESS = "In Progress", "In Progress"
        COMPLETED = "Completed", "Completed"
        CANCELED = "Canceled", "Canceled"

    class ApprovalStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    employee = models.ForeignKey("HR.Employee", on_delete=models.SET_NULL, related_name="tasks", blank=True, null=True)
    project = models.ForeignKey("Projects.Project", on_delete=models.CASCADE, related_name="tasks")
    task_name = models.CharField(max_length=255)
    task_description = models.TextField(blank=True, null=True)
    deadline = models.DateField(null=True, blank=True, help_text="Task deadline (optional, informational only)")
    location = models.CharField(max_length=255, blank=True, null=True)
    time_taken_minutes = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    approval_status = models.CharField(max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING, help_text="Task approval status: pending, approved, or rejected")
    internal_notes = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="tasks_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="tasks_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.task_name


class TaskAttachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="tasks/attachments/")
    notes = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="taskattachments_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="taskattachments_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Attachment {self.id}"


class TaskResource(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="resources")
    resource_name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="taskresources_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="taskresources_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.resource_name

