from django.db import models
from django.contrib.auth.models import User


class ActivityLog(models.Model):
    class EntityType(models.TextChoices):
        AMC = "AMC", "AMC"
        TENDER = "Tender", "Tender"
        TASK = "Task", "Task"
        CLIENT = "Client", "Client"
        PROJECT = "Project", "Project"

    class Action(models.TextChoices):
        CREATED = "Created", "Created"
        UPDATED = "Updated", "Updated"
        DELETED = "Deleted", "Deleted"
        COMPLETED = "Completed", "Completed"
        APPROVED = "Approved", "Approved"
        FILED = "Filed", "Filed"

    entity_type = models.CharField(max_length=20, choices=EntityType.choices)
    entity_id = models.BigIntegerField()
    action = models.CharField(max_length=20, choices=Action.choices)
    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="activitylogs_created", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="activitylogs_updated", blank=True, null=True)

    def __str__(self):
        return f"{self.entity_type} {self.entity_id} - {self.action}"

