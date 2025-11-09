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
    ProjectCreateSerializer,
    ProjectStatisticsSerializer
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
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
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
        
        **Filter Options:**
        - status: Filter by project status (Planned, In Progress, On Hold, Completed, Canceled)
        
        **Query Parameters:**
        - search (optional): Search by project name or client name
        - status (optional): Filter by project status
        
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
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                description='Filter by project status (Planned, In Progress, On Hold, Completed, Canceled)',
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
    
    @swagger_auto_schema(
        operation_id='project_statistics',
        operation_summary="Get Project Management Statistics",
        operation_description="""
        Retrieve statistics for the project management dashboard.
        
        **What it returns:**
        - total_projects: Total number of projects in the system
        - planned_projects: Number of projects with "Planned" status
        - in_progress_projects: Number of projects with "In Progress" status
        - completed_projects: Number of projects with "Completed" status
        - on_hold_projects: Number of projects with "On Hold" status
        - canceled_projects: Number of projects with "Canceled" status
        
        **Use Case:**
        Use this endpoint to populate dashboard tiles showing key metrics for project management.
        """,
        tags=['Project Management'],
        responses={
            200: openapi.Response(
                description="Project management statistics",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'total_projects': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total number of projects'),
                        'planned_projects': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of planned projects'),
                        'in_progress_projects': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of in progress projects'),
                        'completed_projects': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of completed projects'),
                        'on_hold_projects': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of on hold projects'),
                        'canceled_projects': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of canceled projects')
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """Get project management statistics for dashboard"""
        # Total projects
        total_projects = Project.objects.count()
        
        # Projects by status
        planned_projects = Project.objects.filter(status=Project.Status.PLANNED).count()
        in_progress_projects = Project.objects.filter(status=Project.Status.IN_PROGRESS).count()
        completed_projects = Project.objects.filter(status=Project.Status.COMPLETED).count()
        on_hold_projects = Project.objects.filter(status=Project.Status.ON_HOLD).count()
        canceled_projects = Project.objects.filter(status=Project.Status.CANCELED).count()
        
        data = {
            'total_projects': total_projects,
            'planned_projects': planned_projects,
            'in_progress_projects': in_progress_projects,
            'completed_projects': completed_projects,
            'on_hold_projects': on_hold_projects,
            'canceled_projects': canceled_projects
        }
        
        serializer = ProjectStatisticsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
