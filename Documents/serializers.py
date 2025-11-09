from rest_framework import serializers
from .models import DocumentTemplate, DocumentTemplateVersion
from Clients.models import Firm


class DocumentTemplateVersionSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = DocumentTemplateVersion
        fields = [
            'id', 'version_number', 'file', 'file_url', 'file_type', 
            'is_published', 'created_at', 'created_by', 'created_by_username'
        ]
        read_only_fields = ['version_number', 'file_type', 'created_at', 'created_by']
    
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class DocumentTemplateListSerializer(serializers.ModelSerializer):
    firm_name = serializers.CharField(source='firm.firm_name', read_only=True)
    versions = DocumentTemplateVersionSerializer(many=True, read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    published_version = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentTemplate
        fields = [
            'id', 'title', 'category', 'description', 'firm', 'firm_name',
            'versions', 'published_version', 'created_at', 'created_by', 
            'created_by_username'
        ]
        read_only_fields = ['created_at', 'created_by']
    
    def get_published_version(self, obj):
        published_version = obj.versions.filter(is_published=True).first()
        if published_version:
            return DocumentTemplateVersionSerializer(published_version, context=self.context).data
        return None


class DocumentTemplateUploadSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    category = serializers.CharField(max_length=100, allow_blank=True, allow_null=True)
    firm = serializers.PrimaryKeyRelatedField(queryset=Firm.objects.all())
    upload_file = serializers.FileField()
    notes = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    
    def validate_upload_file(self, value):
        """Validate file type"""
        file_extension = value.name.split('.')[-1].lower()
        if file_extension not in ['pdf', 'docx', 'doc']:
            raise serializers.ValidationError("Only PDF and DOCX files are allowed.")
        return value


class BulkDownloadSerializer(serializers.Serializer):
    version_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        help_text='List of version IDs to download'
    )
    template_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        help_text='List of template IDs to download (downloads published version)'
    )
    
    def validate(self, data):
        version_ids = data.get('version_ids', [])
        template_ids = data.get('template_ids', [])
        
        if not version_ids and not template_ids:
            raise serializers.ValidationError(
                "Please provide either version_ids or template_ids"
            )
        return data

