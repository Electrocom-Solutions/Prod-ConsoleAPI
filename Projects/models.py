from django.db import models
from django.contrib.auth.models import User


class Project(models.Model):
    class Status(models.TextChoices):
        PLANNED = "Planned", "Planned"
        IN_PROGRESS = "In Progress", "In Progress"
        ON_HOLD = "On Hold", "On Hold"
        COMPLETED = "Completed", "Completed"
        CANCELED = "Canceled", "Canceled"

    client = models.ForeignKey("Clients.Client", on_delete=models.CASCADE, related_name="projects")
    tender = models.ForeignKey("Tenders.Tender", on_delete=models.SET_NULL, related_name="projects", blank=True, null=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="projects_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="projects_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

