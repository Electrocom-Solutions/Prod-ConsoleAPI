from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Project
from .serializers import (
    ProjectListSerializer,
    ProjectDetailSerializer,
    ProjectCreateSerializer
)


class ProjectViewSet(viewsets.ModelViewSet):
    """
    Project Management APIs
    """
    queryset = Project.objects.select_related('client', 'tender', 'created_by', 'updated_by').all()
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return ProjectListSerializer
        elif self.action in ['retrieve']:
            return ProjectDetailSerializer
        return ProjectCreateSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search by project name or client name
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(client__first_name__icontains=search) |
                Q(client__last_name__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    @swagger_auto_schema(
        operation_id='project_list',
        operation_summary="List All Projects",
        operation_description="""
        Retrieve a list of all projects with filtering and search options.
        
        **What it returns:**
        - List of projects with basic information (name, client, tender, dates, status)
        - Client name and tender name included for easy reference
        
        **Search Options:**
        - search: Search by project name or client name (first name, last name) (case-insensitive partial match)
        
        **Query Parameters:**
        - search (optional): Search by project name or client name
        
        **Pagination:**
        Results are paginated (20 items per page by default) and sorted by creation date (newest first).
        """,
        tags=['Project Management'],
        manual_parameters=[
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description='Search by project name or client name',
                type=openapi.TYPE_STRING,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of projects",
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
        """List all projects with filtering and search"""
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='project_retrieve',
        operation_summary="Get Project Details",
        operation_description="""
        Retrieve detailed information about a specific project.
        
        **What it returns:**
        - Complete project information including all fields
        - Client name and tender name for easy reference
        - Creation and update timestamps
        """,
        tags=['Project Management'],
        responses={
            200: ProjectDetailSerializer()
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """Get project details"""
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='project_create',
        operation_summary="Create New Project",
        operation_description="""
        Create a new project with all required and optional information.
        
        **Required Fields:**
        - name: Project name
        - client: ID of the client associated with this project
        
        **Optional Fields:**
        - tender: ID of the tender associated with this project (if project is linked to a tender)
        - description: Project description
        - start_date: Project start date (YYYY-MM-DD)
        - end_date: Project end date (YYYY-MM-DD)
        - status: Project status (Planned, In Progress, On Hold, Completed, Canceled)
        
        **Validation:**
        - end_date must be after start_date if both are provided
        
        **Response:**
        Returns the created project with all details.
        """,
        tags=['Project Management'],
        request_body=ProjectCreateSerializer,
        responses={
            201: openapi.Response(
                description="Project created successfully",
                schema=ProjectCreateSerializer()
            )
        }
    )
    def create(self, request, *args, **kwargs):
        """Create a new project"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @swagger_auto_schema(
        operation_id='project_update',
        operation_summary="Update Project",
        operation_description="""
        Update an existing project's information. All fields are optional - only provided fields will be updated.
        
        **Fields:**
        Same as create endpoint - all fields are optional for update.
        
        **Validation:**
        - end_date must be after start_date if both are provided and updated.
        
        **Response:**
        Returns the updated project with all details.
        """,
        tags=['Project Management'],
        request_body=ProjectCreateSerializer,
        responses={
            200: openapi.Response(
                description="Project updated successfully",
                schema=ProjectCreateSerializer()
            )
        }
    )
    def update(self, request, *args, **kwargs):
        """Update project information"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_id='project_partial_update',
        operation_summary="Partial Update Project",
        operation_description="""
        Partially update a project's information. Only provided fields will be updated.
        
        **Use Case:**
        Use this endpoint when you only want to update specific fields without affecting others.
        """,
        tags=['Project Management'],
        request_body=ProjectCreateSerializer,
        responses={
            200: openapi.Response(
                description="Project partially updated successfully",
                schema=ProjectCreateSerializer()
            )
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """Partially update project information"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='project_delete',
        operation_summary="Delete Project",
        operation_description="""
        Delete a project from the system. This action is permanent and cannot be undone.
        
        **Warning:**
        Deleting a project will permanently remove it from the system.
        
        **Use Case:**
        Use this endpoint when you need to permanently remove a project from the system.
        """,
        tags=['Project Management'],
        responses={
            204: openapi.Response(description="Project deleted successfully"),
            404: openapi.Response(description="Project not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        """Delete a project"""
        return super().destroy(request, *args, **kwargs)
