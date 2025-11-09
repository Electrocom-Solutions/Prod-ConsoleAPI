from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Max
from django.db import transaction
from django.http import FileResponse, HttpResponse
from urllib.parse import quote
import zipfile
import io
import os
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import DocumentTemplate, DocumentTemplateVersion
from .serializers import (
    DocumentTemplateListSerializer,
    DocumentTemplateUploadSerializer,
    DocumentTemplateVersionSerializer,
    BulkDownloadSerializer
)


class DocumentTemplateViewSet(viewsets.ModelViewSet):
    """
    Document Template Management APIs
    """
    queryset = DocumentTemplate.objects.select_related('firm', 'created_by').prefetch_related('versions', 'versions__created_by').all()
    serializer_class = DocumentTemplateListSerializer
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by category
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter by firm
        firm = self.request.query_params.get('firm', None)
        if firm:
            queryset = queryset.filter(firm_id=firm)
        
        # Search by title
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(title__icontains=search)
        
        return queryset.order_by('-created_at')
    
    @swagger_auto_schema(
        operation_id='document_upload_template',
        operation_summary="Upload Document Template",
        operation_description="""
        Upload a new document template to the system. This endpoint handles document versioning automatically.
        
        **How it works:**
        1. Accepts a document file (PDF or DOCX) along with metadata (title, category, firm, notes)
        2. Checks if a template with the same title, category, and firm already exists
        3. If template exists: Creates a new version (increments version number) and sets it as published
        4. If template is new: Creates a new template with version 1 as published
        5. Only one version can be published at a time - previous versions are automatically unpublished
        
        **Request Fields:**
        - title (required): Name of the document template
        - category (optional): Category/type of the document (e.g., "AMC", "Contract", "Agreement")
        - firm (required): ID of the firm this template belongs to
        - upload_file (required): PDF or DOCX file to upload
        - notes (optional): Additional notes or description about the template
        
        **Response:**
        Returns the template details with the newly created/versioned document information.
        """,
        tags=['Document Management'],
        manual_parameters=[
            openapi.Parameter(
                'title',
                openapi.IN_FORM,
                description='Template title',
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'category',
                openapi.IN_FORM,
                description='Template category',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'firm',
                openapi.IN_FORM,
                description='Firm ID',
                type=openapi.TYPE_INTEGER,
                required=True
            ),
            openapi.Parameter(
                'upload_file',
                openapi.IN_FORM,
                description='PDF or DOCX file',
                type=openapi.TYPE_FILE,
                required=True
            ),
            openapi.Parameter(
                'notes',
                openapi.IN_FORM,
                description='Notes/description',
                type=openapi.TYPE_STRING,
                required=False
            ),
        ],
        responses={
            201: openapi.Response(
                description="Template uploaded successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'template': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'version': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['post'], url_path='upload-template')
    def upload_template(self, request):
        """Upload a new document template with versioning logic"""
        serializer = DocumentTemplateUploadSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        title = serializer.validated_data['title']
        category = serializer.validated_data.get('category', None)
        firm = serializer.validated_data['firm']
        upload_file = serializer.validated_data['upload_file']
        notes = serializer.validated_data.get('notes', None)
        
        # Determine file type from extension
        file_extension = upload_file.name.split('.')[-1].lower()
        if file_extension == 'pdf':
            file_type = DocumentTemplateVersion.FileType.PDF
        elif file_extension in ['docx', 'doc']:
            file_type = DocumentTemplateVersion.FileType.DOCX
        else:
            return Response(
                {'error': 'Invalid file type. Only PDF and DOCX are allowed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Check if template with same title, category, and firm exists
                existing_template = DocumentTemplate.objects.filter(
                    title=title,
                    category=category,
                    firm=firm
                ).first()
                
                if existing_template:
                    # Template exists - create new version
                    # Get the highest version number
                    max_version = existing_template.versions.aggregate(
                        max_version=Max('version_number')
                    )['max_version'] or 0
                    
                    new_version_number = max_version + 1
                    
                    # Set all existing versions to is_published=False
                    existing_template.versions.update(is_published=False)
                    
                    # Create new version with is_published=True
                    new_version = DocumentTemplateVersion.objects.create(
                        template=existing_template,
                        version_number=new_version_number,
                        file=upload_file,
                        file_type=file_type,
                        is_published=True,
                        created_by=request.user
                    )
                    
                    # Update template description if notes provided
                    if notes:
                        existing_template.description = notes
                        existing_template.updated_by = request.user
                        existing_template.save()
                    
                    template_serializer = DocumentTemplateListSerializer(
                        existing_template,
                        context={'request': request}
                    )
                    version_serializer = DocumentTemplateVersionSerializer(
                        new_version,
                        context={'request': request}
                    )
                    
                    return Response({
                        'message': f'Template versioned successfully. New version {new_version_number} created and published.',
                        'template': template_serializer.data,
                        'version': version_serializer.data
                    }, status=status.HTTP_201_CREATED)
                else:
                    # New template - create template with version 1
                    new_template = DocumentTemplate.objects.create(
                        title=title,
                        category=category,
                        firm=firm,
                        description=notes,
                        created_by=request.user
                    )
                    
                    # Create version 1 with is_published=True
                    new_version = DocumentTemplateVersion.objects.create(
                        template=new_template,
                        version_number=1,
                        file=upload_file,
                        file_type=file_type,
                        is_published=True,
                        created_by=request.user
                    )
                    
                    template_serializer = DocumentTemplateListSerializer(
                        new_template,
                        context={'request': request}
                    )
                    version_serializer = DocumentTemplateVersionSerializer(
                        new_version,
                        context={'request': request}
                    )
                    
                    return Response({
                        'message': 'Template created successfully with version 1.',
                        'template': template_serializer.data,
                        'version': version_serializer.data
                    }, status=status.HTTP_201_CREATED)
                    
        except Exception as e:
            return Response(
                {'error': f'Error uploading template: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_id='document_list',
        operation_summary="List All Document Templates",
        operation_description="""
        Retrieve all document templates with their complete version history. This endpoint provides a comprehensive list of all templates in the system.
        
        **What it returns:**
        - List of all document templates with their metadata (title, category, firm, description)
        - All versions for each template (version numbers, file types, published status)
        - Published version highlighted for each template
        - Created by information and timestamps
        
        **Filtering Options:**
        - category: Filter templates by specific category (e.g., "AMC", "Contract")
        - firm: Filter templates by firm ID
        - search: Search templates by title (case-insensitive partial match)
        
        **Query Parameters:**
        - category (optional): Filter by document category
        - firm (optional): Filter by firm ID
        - search (optional): Search by template title (partial match, case-insensitive)
        
        **Pagination:**
        Results are paginated (20 items per page by default) and sorted by creation date (newest first).
        
        **Use Case:**
        Use this endpoint to display a list of all document templates in the UI, with filtering and 
        search capabilities for easy navigation.
        """,
        tags=['Document Management'],
        manual_parameters=[
            openapi.Parameter(
                'category',
                openapi.IN_QUERY,
                description='Filter by document category (e.g., "AMC", "Contract")',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'firm',
                openapi.IN_QUERY,
                description='Filter by firm ID',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description='Search by template title (partial match, case-insensitive)',
                type=openapi.TYPE_STRING,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of document templates with versions",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'results': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT)
                        )
                    }
                )
            )
        }
    )
    def list(self, request, *args, **kwargs):
        """Get all document templates with versions"""
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='document_retrieve',
        operation_summary="Get Template Details",
        operation_description="""
        Retrieve detailed information about a specific document template including all its versions.
        
        **What it returns:**
        - Complete template metadata (title, category, firm, description)
        - All versions of the template with their details:
          * Version numbers
          * File types (PDF or DOCX)
          * Published status
          * Creation dates and creators
          * File URLs for each version
        - Published version clearly identified
        
        **Use Case:**
        Use this endpoint when you need to see the complete version history of a specific template, 
        view all available versions, or check which version is currently published.
        """,
        tags=['Document Management'],
        responses={
            200: openapi.Response(
                description="Document template with versions",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            )
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """Get a specific document template with all versions"""
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='document_download_version',
        operation_summary="Download Specific Version",
        operation_description="""
        Download a specific version of a document template by providing both template ID and version ID.
        
        **What it does:**
        - Validates that the version belongs to the specified template
        - Retrieves the file associated with that version
        - Returns the file as a downloadable attachment
        
        **File Naming:**
        Downloaded file will be named: `{template_title}_v{version_number}.{extension}`
        Example: "AMC Service Agreement_v2.pdf"
        
        **Use Case:**
        Use this when you need to download a specific historical version of a document, 
        not just the current published version.
        
        **Path Parameters:**
        - template_id: ID of the template
        - version_id: ID of the specific version to download
        """,
        tags=['Document Management'],
        manual_parameters=[
            openapi.Parameter(
                'version_id',
                openapi.IN_PATH,
                description='Version ID to download',
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="File download",
                schema=openapi.Schema(type=openapi.TYPE_FILE)
            ),
            404: openapi.Response(description="Version not found")
        }
    )
    @action(detail=True, methods=['get'], url_path='download-version/(?P<version_id>[0-9]+)')
    def download_version(self, request, pk=None, version_id=None):
        """Download a specific document version by version ID"""
        try:
            version = DocumentTemplateVersion.objects.select_related('template').get(
                id=version_id,
                template_id=pk
            )
            
            if not version.file:
                return Response(
                    {'error': 'File not found for this version'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get file extension
            file_extension = os.path.splitext(version.file.name)[1] or f'.{version.file_type}'
            filename = f"{version.template.title}_v{version.version_number}{file_extension}"
            
            # Create file response
            response = FileResponse(
                version.file.open('rb'),
                as_attachment=True,
                filename=filename
            )
            response['Content-Disposition'] = f'attachment; filename="{quote(filename)}"'
            return response
            
        except DocumentTemplateVersion.DoesNotExist:
            return Response(
                {'error': 'Version not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Error downloading file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_id='document_download_published',
        operation_summary="Download Published Version",
        operation_description="""
        Download the currently published (active) version of a document template.
        
        **What it does:**
        - Finds the template by ID
        - Retrieves the version marked as published (is_published=True)
        - Returns the published file as a downloadable attachment
        
        **File Naming:**
        Downloaded file will be named: `{template_title}_v{version_number}.{extension}`
        Example: "AMC Service Agreement_v3.pdf"
        
        **Use Case:**
        This is the most common download endpoint - use it when you want the current/active 
        version of a document. Perfect for users who just need the latest published document.
        
        **Path Parameters:**
        - template_id: ID of the template whose published version you want to download
        """,
        tags=['Document Management'],
        responses={
            200: openapi.Response(
                description="File download",
                schema=openapi.Schema(type=openapi.TYPE_FILE)
            ),
            404: openapi.Response(description="Published version not found")
        }
    )
    @action(detail=True, methods=['get'], url_path='download-published')
    def download_published(self, request, pk=None):
        """Download the published version of a document template"""
        try:
            template = DocumentTemplate.objects.get(pk=pk)
            version = template.versions.filter(is_published=True).first()
            
            if not version:
                return Response(
                    {'error': 'No published version found for this template'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            if not version.file:
                return Response(
                    {'error': 'File not found for this version'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get file extension
            file_extension = os.path.splitext(version.file.name)[1] or f'.{version.file_type}'
            filename = f"{template.title}_v{version.version_number}{file_extension}"
            
            # Create file response
            response = FileResponse(
                version.file.open('rb'),
                as_attachment=True,
                filename=filename
            )
            response['Content-Disposition'] = f'attachment; filename="{quote(filename)}"'
            return response
            
        except DocumentTemplate.DoesNotExist:
            return Response(
                {'error': 'Template not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Error downloading file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_id='document_download_version_direct',
        operation_summary="Download Version by Version ID",
        operation_description="""
        Download a document version directly using only the version ID. This is a simplified endpoint 
        designed for easier use in UI components.
        
        **What it does:**
        - Accepts only the version ID (no need to know template ID)
        - Retrieves the version and its associated template
        - Returns the file as a downloadable attachment
        
        **File Naming:**
        Downloaded file will be named: `{template_title}_v{version_number}.{extension}`
        Example: "AMC Service Agreement_v2.pdf"
        
        **Use Case:**
        Ideal for UI components that display version lists and need a simple download button. 
        When you have a version ID from the version list, use this endpoint instead of the 
        template-specific download endpoints.
        
        **Query Parameters:**
        - version_id (required): ID of the version to download
        """,
        tags=['Document Management'],
        manual_parameters=[
            openapi.Parameter(
                'version_id',
                openapi.IN_QUERY,
                description='Version ID to download',
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="File download",
                schema=openapi.Schema(type=openapi.TYPE_FILE)
            ),
            404: openapi.Response(description="Version not found")
        }
    )
    @action(detail=False, methods=['get'], url_path='download-version')
    def download_version_direct(self, request):
        """Download a document version directly by version ID (simpler endpoint for UI)"""
        version_id = request.query_params.get('version_id', None)
        
        if not version_id:
            return Response(
                {'error': 'version_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            version = DocumentTemplateVersion.objects.select_related('template').get(id=version_id)
            
            if not version.file:
                return Response(
                    {'error': 'File not found for this version'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get file extension
            file_extension = os.path.splitext(version.file.name)[1] or f'.{version.file_type}'
            filename = f"{version.template.title}_v{version.version_number}{file_extension}"
            
            # Create file response
            response = FileResponse(
                version.file.open('rb'),
                as_attachment=True,
                filename=filename
            )
            response['Content-Disposition'] = f'attachment; filename="{quote(filename)}"'
            return response
            
        except DocumentTemplateVersion.DoesNotExist:
            return Response(
                {'error': 'Version not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Error downloading file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_id='document_bulk_download',
        operation_summary="Bulk Download Documents",
        operation_description="""
        Download multiple documents at once as a single ZIP file. This endpoint allows you to select 
        multiple documents and download them all in one operation.
        
        **What it does:**
        1. Accepts a list of version IDs and/or template IDs
        2. For version IDs: Downloads the specific versions requested
        3. For template IDs: Downloads the published version of each template
        4. Creates a ZIP file containing all selected documents
        5. Returns the ZIP file for download
        
        **Request Body:**
        ```json
        {
          "version_ids": [1, 2, 3],      // Optional: Array of version IDs to download
          "template_ids": [4, 5, 6]      // Optional: Array of template IDs (downloads published version)
        }
        ```
        
        **Features:**
        - Supports both version IDs and template IDs in the same request
        - Automatically handles duplicates (same file won't be added twice)
        - Works with both local file storage and cloud storage (S3, etc.)
        - Handles missing or inaccessible files gracefully (skips them)
        
        **File Naming in ZIP:**
        Each file in the ZIP is named: `{template_title}_v{version_number}.{extension}`
        Example: "AMC Service Agreement_v2.pdf"
        
        **Use Case:**
        Perfect for bulk actions in the UI where users select multiple documents and want to 
        download them all at once. Saves time compared to downloading files one by one.
        
        **Response:**
        Returns a ZIP file named "documents.zip" containing all selected documents.
        """,
        request_body=BulkDownloadSerializer,
        responses={
            200: openapi.Response(
                description="ZIP file download",
                schema=openapi.Schema(type=openapi.TYPE_FILE)
            ),
            400: openapi.Response(
                description="Invalid request or no files to download",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        },
        tags=['Document Management']
    )
    @action(detail=False, methods=['post'], url_path='bulk-download', parser_classes=[JSONParser])
    def bulk_download(self, request):
        """Download multiple document versions as a zip file"""
        serializer = BulkDownloadSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        version_ids = serializer.validated_data.get('version_ids', [])
        template_ids = serializer.validated_data.get('template_ids', [])
        
        try:
            # Create in-memory zip file
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                files_added = 0
                
                # Download versions by version IDs
                if version_ids:
                    versions = DocumentTemplateVersion.objects.select_related('template').filter(
                        id__in=version_ids
                    )
                    
                    for version in versions:
                        if version.file:
                            try:
                                # Try to get file path or read from storage
                                if hasattr(version.file, 'path') and os.path.exists(version.file.path):
                                    file_path = version.file.path
                                else:
                                    # For cloud storage, read into memory first
                                    file_path = version.file.read()
                                    version.file.seek(0)  # Reset file pointer
                                
                                file_extension = os.path.splitext(version.file.name)[1] or f'.{version.file_type}'
                                filename = f"{version.template.title}_v{version.version_number}{file_extension}"
                                
                                # Add file to zip
                                if isinstance(file_path, bytes):
                                    # If file is in memory, write from bytes
                                    zip_file.writestr(filename, file_path)
                                else:
                                    # If file is on disk, write from path
                                    zip_file.write(file_path, filename)
                                files_added += 1
                            except Exception as e:
                                # Skip files that can't be read
                                continue
                
                # Download published versions by template IDs
                if template_ids:
                    templates = DocumentTemplate.objects.prefetch_related('versions').filter(
                        id__in=template_ids
                    )
                    
                    for template in templates:
                        published_version = template.versions.filter(is_published=True).first()
                        if published_version and published_version.file:
                            try:
                                # Try to get file path or read from storage
                                if hasattr(published_version.file, 'path') and os.path.exists(published_version.file.path):
                                    file_path = published_version.file.path
                                else:
                                    # For cloud storage, read into memory first
                                    file_path = published_version.file.read()
                                    published_version.file.seek(0)  # Reset file pointer
                                
                                file_extension = os.path.splitext(published_version.file.name)[1] or f'.{published_version.file_type}'
                                filename = f"{template.title}_v{published_version.version_number}{file_extension}"
                                
                                # Check if file already exists in zip (avoid duplicates)
                                if filename not in zip_file.namelist():
                                    # Add file to zip
                                    if isinstance(file_path, bytes):
                                        # If file is in memory, write from bytes
                                        zip_file.writestr(filename, file_path)
                                    else:
                                        # If file is on disk, write from path
                                        zip_file.write(file_path, filename)
                                    files_added += 1
                            except Exception as e:
                                # Skip files that can't be read
                                continue
                
                if files_added == 0:
                    return Response(
                        {'error': 'No files found to download'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Prepare response
            zip_buffer.seek(0)
            zip_content = zip_buffer.read()
            
            response = HttpResponse(zip_content, content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename="documents.zip"'
            response['Content-Length'] = len(zip_content)
            
            return response
            
        except Exception as e:
            return Response(
                {'error': f'Error creating zip file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
