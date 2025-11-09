from django.db import models
from django.contrib.auth.models import User


class DocumentTemplate(models.Model):
    firm = models.ForeignKey("Clients.Firm", on_delete=models.CASCADE, related_name="document_templates")
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="documenttemplates_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="documenttemplates_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class DocumentTemplateVersion(models.Model):
    class FileType(models.TextChoices):
        PDF = "pdf", "pdf"
        DOCX = "docx", "docx"

    template = models.ForeignKey(DocumentTemplate, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    file = models.FileField(upload_to="documents/templates/")
    file_type = models.CharField(max_length=10, choices=FileType.choices)
    is_published = models.BooleanField(default=False)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="documenttemplateversions_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="documenttemplateversions_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("template", "version_number")

    def __str__(self):
        return f"{self.template.title} v{self.version_number}"


class CombinedDocument(models.Model):
    template = models.ForeignKey(DocumentTemplate, on_delete=models.CASCADE, related_name="combined_documents")
    title = models.CharField(max_length=255)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="combined_documents_created", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="combined_documents_updated", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

