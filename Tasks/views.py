from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q, Sum, Count
from django.db.models.functions import Coalesce
from django.db import transaction
from datetime import date, datetime, timedelta
from calendar import monthrange
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Task, TaskResource, TaskAttachment
from .serializers import (
    TaskStatisticsSerializer,
    TaskListSerializer,
    TaskDetailSerializer,
    TaskCreateSerializer,
    BulkApproveSerializer,
    TaskAttachmentUploadSerializer,
    TaskResourceCreateSerializer,
    TaskAttachmentSerializer,
    TaskResourcesDashboardSerializer,
    TaskResourcesStatisticsSerializer
)
from Analytics.models import ActivityLog
from Notifications.utils import send_notification_to_owners, send_notification_to_user


class TaskViewSet(viewsets.ModelViewSet):
    """
    Task Management APIs
    """
    queryset = Task.objects.select_related(
        'employee', 'employee__profile', 'employee__profile__user',
        'project', 'project__client', 'created_by', 'updated_by'
    ).prefetch_related('attachments', 'resources').all()
    parser_classes = [MultiPartParser, FormParser]
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return TaskListSerializer
        elif self.action in ['retrieve']:
            return TaskDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return TaskCreateSerializer
        return TaskListSerializer
    
    def _get_date_range(self, filter_type):
        """Get date range based on filter type"""
        today = date.today()
        
        if filter_type == 'today':
            return today, today
        elif filter_type == 'this_week':
            # Get start of week (Monday)
            days_since_monday = today.weekday()
            start_of_week = today - timedelta(days=days_since_monday)
            end_of_week = start_of_week + timedelta(days=6)
            return start_of_week, end_of_week
        elif filter_type == 'this_month':
            # Get start and end of current month
            start_of_month = today.replace(day=1)
            last_day = monthrange(today.year, today.month)[1]
            end_of_month = today.replace(day=last_day)
            return start_of_month, end_of_month
        else:  # 'all' or None
            return None, None
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search by employee name, project name, or client name
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(employee__profile__user__first_name__icontains=search) |
                Q(employee__profile__user__last_name__icontains=search) |
                Q(employee__profile__user__username__icontains=search) |
                Q(project__name__icontains=search) |
                Q(project__client__first_name__icontains=search) |
                Q(project__client__last_name__icontains=search) |
                Q(project__client__name__icontains=search)
            )
        
        # Filter by project
        project_filter = self.request.query_params.get('project', None)
        if project_filter:
            queryset = queryset.filter(project_id=project_filter)
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Date filter
        date_filter = self.request.query_params.get('date_filter', 'all').lower()
        start_date, end_date = self._get_date_range(date_filter)
        if date_filter != 'all' and start_date and end_date:
            queryset = queryset.filter(
                task_date__gte=start_date,
                task_date__lte=end_date
            )
        
        return queryset.order_by('-task_date', '-created_at')
    
    @swagger_auto_schema(
        operation_id='task_statistics',
        operation_summary="Get Task Management Statistics",
        operation_description="""
        Retrieve statistics for the task management dashboard with date filtering support.
        
        **What it returns:**
        - total_tasks: Total number of tasks (within the selected date range)
        - pending_approval: Number of tasks with "Draft" status (awaiting approval)
        - approved_tasks: Number of tasks with "In Progress" or "Completed" status (approved tasks)
        - total_timings: Total time taken by all tasks in hours (e.g., 39.0hrs)
        - total_resource_cost: Total resource cost from all tasks (sum of all TaskResource.total_cost)
        
        **Date Filtering Options:**
        The statistics can be filtered by date range using the `filter` query parameter:
        - `today`: Statistics for tasks with task_date = today
        - `this_week`: Statistics for tasks with task_date within the current week (Monday to Sunday)
        - `this_month`: Statistics for tasks with task_date within the current month
        - `all`: Statistics for all tasks in the system (no date filter) - this is the default
        
        **Query Parameters:**
        - filter (optional): Date filter type - 'today', 'this_week', 'this_month', or 'all' (default: 'all')
        
        **Use Case:**
        Use this endpoint to populate dashboard tiles showing key metrics for task management.
        The date filters allow users to view statistics for different time periods.
        
        **Example:**
        - GET /api/tasks/statistics/?filter=today - Get statistics for today's tasks
        - GET /api/tasks/statistics/?filter=this_week - Get statistics for this week's tasks
        - GET /api/tasks/statistics/?filter=this_month - Get statistics for this month's tasks
        - GET /api/tasks/statistics/?filter=all - Get statistics for all tasks (default)
        """,
        tags=['Task Management'],
        manual_parameters=[
            openapi.Parameter(
                'filter',
                openapi.IN_QUERY,
                description='Date filter type: today, this_week, this_month, or all (default: all)',
                type=openapi.TYPE_STRING,
                enum=['today', 'this_week', 'this_month', 'all'],
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="Task management statistics",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'total_tasks': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total number of tasks'),
                        'pending_approval': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of tasks pending approval (Draft status)'),
                        'approved_tasks': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of approved tasks (In Progress or Completed)'),
                        'total_timings': openapi.Schema(type=openapi.TYPE_NUMBER, description='Total time in hours (e.g., 39.0hrs)'),
                        'total_resource_cost': openapi.Schema(type=openapi.TYPE_NUMBER, description='Total resource cost from all tasks')
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """Get task management statistics for dashboard with date filtering"""
        # Get filter type from query parameters
        filter_type = request.query_params.get('filter', 'all').lower()
        
        # Validate filter type
        valid_filters = ['today', 'this_week', 'this_month', 'all']
        if filter_type not in valid_filters:
            return Response(
                {'error': f'Invalid filter type. Must be one of: {", ".join(valid_filters)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get date range based on filter
        start_date, end_date = self._get_date_range(filter_type)
        
        # Base queryset
        tasks_queryset = Task.objects.all()
        
        # Apply date filter if not 'all'
        if filter_type != 'all' and start_date and end_date:
            tasks_queryset = tasks_queryset.filter(
                task_date__gte=start_date,
                task_date__lte=end_date
            )
        
        # Get task IDs for resource cost calculation
        task_ids = list(tasks_queryset.values_list('id', flat=True))
        
        # Calculate statistics
        # Total tasks
        total_tasks = tasks_queryset.count()
        
        # Pending approval (Draft status)
        pending_approval = tasks_queryset.filter(status=Task.Status.DRAFT).count()
        
        # Approved tasks (In Progress or Completed)
        approved_tasks = tasks_queryset.filter(
            status__in=[Task.Status.IN_PROGRESS, Task.Status.COMPLETED]
        ).count()
        
        # Total timings (convert minutes to hours)
        total_minutes = tasks_queryset.aggregate(
            total=Coalesce(Sum('time_taken_minutes'), 0)
        )['total'] or 0
        total_timings = float(total_minutes) / 60.0  # Convert minutes to hours
        
        # Total resource cost (sum of all TaskResource.total_cost for these tasks)
        if task_ids:
            total_resource_cost = TaskResource.objects.filter(
                task_id__in=task_ids
            ).aggregate(
                total=Coalesce(Sum('total_cost'), 0)
            )['total'] or 0
        else:
            total_resource_cost = 0
        
        data = {
            'total_tasks': total_tasks,
            'pending_approval': pending_approval,
            'approved_tasks': approved_tasks,
            'total_timings': round(total_timings, 2),
            'total_resource_cost': float(total_resource_cost)
        }
        
        serializer = TaskStatisticsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_id='task_list',
        operation_summary="List All Tasks",
        operation_description="""
        Retrieve a list of all tasks with filtering and search options.
        
        **What it returns:**
        - List of tasks with basic information (task name, date, location, time taken, status)
        - Employee name, project name, and client name for easy reference
        - Time taken in both minutes and hours
        
        **Search Options:**
        - search: Search by employee name (first name, last name, username), project name, or client name (case-insensitive partial match)
        
        **Filtering Options:**
        - project: Filter by project ID
        - status: Filter by task status (Draft, In Progress, Completed, Canceled)
        - date_filter: Filter by date range (today, this_week, this_month, all)
          * today: Tasks with task_date = today
          * this_week: Tasks with task_date within the current week (Monday to Sunday)
          * this_month: Tasks with task_date within the current month
          * all: All tasks (no date filter) - this is the default
        
        **Query Parameters:**
        - search (optional): Search by employee name, project name, or client name
        - project (optional): Filter by project ID
        - status (optional): Filter by task status
        - date_filter (optional): Filter by date range (today, this_week, this_month, all)
        
        **Pagination:**
        Results are paginated (20 items per page by default) and sorted by task date (newest first).
        """,
        tags=['Task Management'],
        manual_parameters=[
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description='Search by employee name, project name, or client name',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'project',
                openapi.IN_QUERY,
                description='Filter by project ID',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                description='Filter by task status (Draft, In Progress, Completed, Canceled)',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'date_filter',
                openapi.IN_QUERY,
                description='Filter by date range (today, this_week, this_month, all)',
                type=openapi.TYPE_STRING,
                enum=['today', 'this_week', 'this_month', 'all'],
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of tasks",
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
        """List all tasks with filtering and search"""
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='task_retrieve',
        operation_summary="Get Task Details",
        operation_description="""
        Retrieve detailed information about a specific task including all related data.
        
        **What it returns:**
        - Complete task information:
          * Task Name, Task Description, Task Date, Location
          * Time Taken (in minutes and hours)
          * Status, Internal Notes
        - Related information:
          * Project name and client name
          * Employee name (if assigned)
        - Task attachments: All files attached to the task
        - Task resources: All resources used in the task with costs
        - Activity feed: All activities related to this task
        
        **Use Case:**
        Use this endpoint to display complete task information in the task detail page, including all related documents, resources, and activity history.
        """,
        tags=['Task Management'],
        responses={
            200: TaskDetailSerializer()
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """Get task details"""
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='task_bulk_approve',
        operation_summary="Mark Multiple Tasks as Approved",
        operation_description="""
        Mark multiple tasks as approved (change status from Draft to In Progress).
        
        **What it does:**
        - Accepts a list of task IDs
        - Updates all selected tasks' status from "Draft" to "In Progress"
        - Creates activity log entries for each approved task
        - Returns the number of tasks approved and any errors
        
        **Request Body:**
        ```json
        {
          "task_ids": [1, 2, 3, 4, 5]
        }
        ```
        
        **Validation:**
        - Only tasks with "Draft" status can be approved
        - Tasks that are already in other statuses will be skipped
        - All operations are performed in a database transaction for data consistency
        
        **Response:**
        Returns the number of tasks approved and any errors encountered.
        
        **Use Case:**
        Use this endpoint when users select multiple tasks and click "Mark as Approved" button to approve them all at once.
        """,
        tags=['Task Management'],
        request_body=BulkApproveSerializer,
        responses={
            200: openapi.Response(
                description="Tasks approved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'approved_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of tasks approved'),
                        'skipped_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of tasks skipped (not in Draft status)'),
                        'errors': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING),
                            description='List of errors encountered'
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid request data",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['post'], url_path='bulk-approve')
    def bulk_approve(self, request):
        """Mark multiple tasks as approved"""
        serializer = BulkApproveSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        task_ids = serializer.validated_data['task_ids']
        
        if not task_ids:
            return Response(
                {'error': 'At least one task ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Get tasks that are in Draft status
                tasks_to_approve = Task.objects.filter(
                    id__in=task_ids,
                    status=Task.Status.DRAFT
                )
                
                approved_count = 0
                skipped_count = 0
                errors = []
                
                for task in tasks_to_approve:
                    try:
                        # Update task status to In Progress (approved)
                        task.status = Task.Status.IN_PROGRESS
                        task.updated_by = request.user
                        task.save()
                        
                        # Create activity log
                        ActivityLog.objects.create(
                            entity_type=ActivityLog.EntityType.TASK,
                            entity_id=task.id,
                            action=ActivityLog.Action.APPROVED,
                            description=f"Task {task.task_name} approved",
                            created_by=request.user
                        )
                        
                        # Notify employee when task is approved
                        if task.employee and task.employee.profile and task.employee.profile.user:
                            employee_user = task.employee.profile.user
                            send_notification_to_user(
                                user=employee_user,
                                title="Task Approved",
                                message=f"Your task '{task.task_name}' has been approved",
                                notification_type="Task",
                                created_by=request.user
                            )
                        
                        approved_count += 1
                    except Exception as e:
                        errors.append(f"Error approving task {task.id}: {str(e)}")
                
                # Count skipped tasks (not in Draft status)
                skipped_count = len(task_ids) - tasks_to_approve.count()
                
                # Check for invalid task IDs
                valid_task_ids = set(tasks_to_approve.values_list('id', flat=True))
                invalid_task_ids = set(task_ids) - valid_task_ids
                
                if invalid_task_ids:
                    # Check if they exist but are not in Draft status
                    existing_tasks = Task.objects.filter(id__in=invalid_task_ids)
                    existing_ids = set(existing_tasks.values_list('id', flat=True))
                    non_existent_ids = invalid_task_ids - existing_ids
                    
                    if non_existent_ids:
                        errors.append(f"Tasks not found: {', '.join(map(str, non_existent_ids))}")
                
                return Response({
                    'approved_count': approved_count,
                    'skipped_count': skipped_count,
                    'errors': errors if errors else None
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            return Response(
                {'error': f'Error approving tasks: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_id='task_create',
        operation_summary="Create New Task",
        operation_description="""
        Create a new task with all required and optional information.
        
        **Required Fields:**
        - project: ID of the project associated with this task
        - deadline: Task deadline/date (YYYY-MM-DD) - this maps to task_date
        - task_name: Name of the task
        
        **Optional Fields:**
        - employee: ID of the employee assigned to this task
        - status: Task status (Draft, In Progress, Completed, Canceled) - default: Draft
        - estimated_time: Estimated time in minutes - this maps to time_taken_minutes
        - location: Location where the task will be performed
        - task_description: Description of the task
        
        **Response:**
        Returns the created task with all details.
        """,
        tags=['Task Management'],
        request_body=TaskCreateSerializer,
        responses={
            201: openapi.Response(
                description="Task created successfully",
                schema=TaskCreateSerializer()
            )
        }
    )
    def create(self, request, *args, **kwargs):
        """Create a new task"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Create activity log
        task = serializer.instance
        ActivityLog.objects.create(
            entity_type=ActivityLog.EntityType.TASK,
            entity_id=task.id,
            action=ActivityLog.Action.CREATED,
            description=f"Task {task.task_name} created",
            created_by=request.user
        )
        
        # Notify owner when employee creates a task
        if not request.user.is_superuser:  # If created by employee (not owner)
            employee_name = request.user.get_full_name() or request.user.username
            send_notification_to_owners(
                title="New Task Created",
                message=f"Employee {employee_name} has created a new task: {task.task_name}",
                notification_type="Task",
                created_by=request.user
            )
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @swagger_auto_schema(
        operation_id='task_update',
        operation_summary="Update Task",
        operation_description="""
        Update an existing task's information. All fields are optional - only provided fields will be updated.
        
        **Fields:**
        Same as create endpoint - all fields are optional for update.
        
        **Response:**
        Returns the updated task with all details.
        """,
        tags=['Task Management'],
        request_body=TaskCreateSerializer,
        responses={
            200: openapi.Response(
                description="Task updated successfully",
                schema=TaskCreateSerializer()
            )
        }
    )
    def update(self, request, *args, **kwargs):
        """Update task information"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        old_status = instance.status
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Refresh instance to get updated status
        instance.refresh_from_db()
        new_status = instance.status
        
        # Create activity log
        ActivityLog.objects.create(
            entity_type=ActivityLog.EntityType.TASK,
            entity_id=instance.id,
            action=ActivityLog.Action.UPDATED,
            description=f"Task {instance.task_name} updated",
            created_by=request.user
        )
        
        # Notify owner when employee marks task as completed
        if not request.user.is_superuser and old_status != Task.Status.COMPLETED and new_status == Task.Status.COMPLETED:
            employee_name = request.user.get_full_name() or request.user.username
            send_notification_to_owners(
                title="Task Completed",
                message=f"Employee {employee_name} has marked task '{instance.task_name}' as completed",
                notification_type="Task",
                created_by=request.user
            )
        
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_id='task_partial_update',
        operation_summary="Partial Update Task",
        operation_description="""
        Partially update a task's information. Only provided fields will be updated.
        
        **Use Case:**
        Use this endpoint when you only want to update specific fields without affecting others.
        """,
        tags=['Task Management'],
        request_body=TaskCreateSerializer,
        responses={
            200: openapi.Response(
                description="Task partially updated successfully",
                schema=TaskCreateSerializer()
            )
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """Partially update task information"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='task_delete',
        operation_summary="Delete Task",
        operation_description="""
        Delete a task from the system. This action is permanent and cannot be undone.
        
        **Warning:**
        Deleting a task will also delete all associated attachments and resources.
        
        **Use Case:**
        Use this endpoint when you need to permanently remove a task from the system.
        """,
        tags=['Task Management'],
        responses={
            204: openapi.Response(description="Task deleted successfully"),
            404: openapi.Response(description="Task not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        """Delete a task"""
        instance = self.get_object()
        task_name = instance.task_name
        task_id = instance.id
        
        # Create activity log before deletion
        ActivityLog.objects.create(
            entity_type=ActivityLog.EntityType.TASK,
            entity_id=task_id,
            action=ActivityLog.Action.DELETED,
            description=f"Task {task_name} deleted",
            created_by=request.user
        )
        
        return super().destroy(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='task_attach_document',
        operation_summary="Attach Document to Task",
        operation_description="""
        Attach a document to a task. These documents are stored in the TaskAttachment table.
        
        **Request Fields:**
        - file (required): Document file to upload
        - notes (optional): Notes or description about the document
        
        **Response:**
        Returns the created document record with file URL.
        """,
        tags=['Task Management'],
        request_body=TaskAttachmentUploadSerializer,
        responses={
            201: openapi.Response(
                description="Document attached successfully",
                schema=TaskAttachmentSerializer()
            )
        }
    )
    @action(detail=True, methods=['post'], url_path='attach-document')
    def attach_document(self, request, pk=None):
        """Attach a document to a task"""
        task = self.get_object()
        serializer = TaskAttachmentUploadSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        file = serializer.validated_data['file']
        notes = serializer.validated_data.get('notes', None)
        
        try:
            attachment = TaskAttachment.objects.create(
                task=task,
                file=file,
                notes=notes,
                created_by=request.user
            )
            
            # Create activity log
            ActivityLog.objects.create(
                entity_type=ActivityLog.EntityType.TASK,
                entity_id=task.id,
                action=ActivityLog.Action.UPDATED,
                description=f"Document attached to task {task.task_name}",
                created_by=request.user
            )
            
            attachment_serializer = TaskAttachmentSerializer(attachment, context={'request': request})
            return Response(attachment_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Error attaching document: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_id='task_attach_resource',
        operation_summary="Attach Resource to Task",
        operation_description="""
        Attach a resource to a task. These resources are stored in the TaskResource table.
        
        **Request Fields:**
        - resource_name (required): Name of the resource
        - quantity (required): Quantity of the resource
        - unit_cost (required): Cost per unit
        - total_cost (optional): Total cost (will be calculated as quantity * unit_cost if not provided)
        
        **Response:**
        Returns the created resource record.
        """,
        tags=['Task Management'],
        request_body=TaskResourceCreateSerializer,
        responses={
            201: openapi.Response(
                description="Resource attached successfully",
                schema=TaskResourceCreateSerializer()
            )
        }
    )
    @action(detail=True, methods=['post'], url_path='attach-resource')
    def attach_resource(self, request, pk=None):
        """Attach a resource to a task"""
        task = self.get_object()
        serializer = TaskResourceCreateSerializer(
            data=request.data,
            context={'task': task, 'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            resource = serializer.save()
            
            # Create activity log
            ActivityLog.objects.create(
                entity_type=ActivityLog.EntityType.TASK,
                entity_id=task.id,
                action=ActivityLog.Action.UPDATED,
                description=f"Resource {resource.resource_name} attached to task {task.task_name}",
                created_by=request.user
            )
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Error attaching resource: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_id='task_delete_document',
        operation_summary="Delete Document from Task",
        operation_description="""
        Delete a document attached to a task. This action is permanent and cannot be undone.
        
        **What it does:**
        - Validates that the document belongs to the specified task
        - Deletes the document from the TaskAttachment table
        - Creates an activity log entry
        
        **Path Parameters:**
        - task_id: ID of the task
        - document_id: ID of the document to delete
        
        **Response:**
        Returns success message upon deletion.
        """,
        tags=['Task Management'],
        responses={
            200: openapi.Response(
                description="Document deleted successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message')
                    }
                )
            ),
            404: openapi.Response(description="Document not found")
        }
    )
    @action(detail=True, methods=['delete'], url_path='delete-document/(?P<document_id>[0-9]+)')
    def delete_document(self, request, pk=None, document_id=None):
        """Delete a document from a task"""
        try:
            task = self.get_object()
            document = TaskAttachment.objects.get(
                id=document_id,
                task_id=pk
            )
            
            document_name = document.file.name.split('/')[-1] if document.file else f"Document {document_id}"
            
            # Delete the document
            document.delete()
            
            # Create activity log
            ActivityLog.objects.create(
                entity_type=ActivityLog.EntityType.TASK,
                entity_id=task.id,
                action=ActivityLog.Action.UPDATED,
                description=f"Document {document_name} deleted from task {task.task_name}",
                created_by=request.user
            )
            
            return Response(
                {'message': 'Document deleted successfully'},
                status=status.HTTP_200_OK
            )
            
        except TaskAttachment.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Error deleting document: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_id='task_delete_resource',
        operation_summary="Delete Resource from Task",
        operation_description="""
        Delete a resource attached to a task. This action is permanent and cannot be undone.
        
        **What it does:**
        - Validates that the resource belongs to the specified task
        - Deletes the resource from the TaskResource table
        - Creates an activity log entry
        
        **Path Parameters:**
        - task_id: ID of the task
        - resource_id: ID of the resource to delete
        
        **Response:**
        Returns success message upon deletion.
        """,
        tags=['Task Management'],
        responses={
            200: openapi.Response(
                description="Resource deleted successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message')
                    }
                )
            ),
            404: openapi.Response(description="Resource not found")
        }
    )
    @action(detail=True, methods=['delete'], url_path='delete-resource/(?P<resource_id>[0-9]+)')
    def delete_resource(self, request, pk=None, resource_id=None):
        """Delete a resource from a task"""
        try:
            task = self.get_object()
            resource = TaskResource.objects.get(
                id=resource_id,
                task_id=pk
            )
            
            resource_name = resource.resource_name
            
            # Delete the resource
            resource.delete()
            
            # Create activity log
            ActivityLog.objects.create(
                entity_type=ActivityLog.EntityType.TASK,
                entity_id=task.id,
                action=ActivityLog.Action.UPDATED,
                description=f"Resource {resource_name} deleted from task {task.task_name}",
                created_by=request.user
            )
            
            return Response(
                {'message': 'Resource deleted successfully'},
                status=status.HTTP_200_OK
            )
            
        except TaskResource.DoesNotExist:
            return Response(
                {'error': 'Resource not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Error deleting resource: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TaskResourcesDashboardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Task Resources Dashboard APIs
    """
    queryset = Task.objects.select_related(
        'employee', 'employee__profile', 'employee__profile__user',
        'project', 'project__client', 'created_by', 'updated_by'
    ).prefetch_related('resources').filter(
        resources__isnull=False
    ).distinct()
    serializer_class = TaskResourcesDashboardSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by month and year
        month_filter = self.request.query_params.get('month', None)
        year_filter = self.request.query_params.get('year', None)
        
        if month_filter and year_filter:
            # Filter by specific month and year
            month = int(month_filter)
            year = int(year_filter)
            # Get first and last day of the month
            first_day = date(year, month, 1)
            last_day = date(year, month, monthrange(year, month)[1])
            queryset = queryset.filter(
                task_date__gte=first_day,
                task_date__lte=last_day
            )
        
        # Search by employee, client, project, task name
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(task_name__icontains=search) |
                Q(employee__profile__user__first_name__icontains=search) |
                Q(employee__profile__user__last_name__icontains=search) |
                Q(employee__profile__user__username__icontains=search) |
                Q(project__name__icontains=search) |
                Q(project__client__first_name__icontains=search) |
                Q(project__client__last_name__icontains=search) |
                Q(project__client__name__icontains=search)
            )
        
        return queryset.order_by('-task_date', '-created_at')
    
    @swagger_auto_schema(
        operation_id='task_resources_statistics',
        operation_summary="Get Task Resources Dashboard Statistics",
        operation_description="""
        Retrieve statistics for the task resources dashboard.
        
        **What it returns:**
        - total_tasks: Total number of tasks that have resources (in the selected month/year)
        - total_cost: Total cost of all resources used in tasks (sum of all TaskResource.total_cost) for the selected month/year
        
        **Month/Year Filtering:**
        The statistics can be filtered by month and year using query parameters.
        - If month and year are provided, statistics are calculated for that specific month/year
        - If not provided, statistics are calculated for all tasks with resources
        
        **Query Parameters:**
        - month (optional): Filter by month (1-12), must be used with year
        - year (optional): Filter by year (YYYY), must be used with month
        
        **Use Case:**
        Use this endpoint to populate dashboard tiles showing key metrics for task resources.
        """,
        tags=['Task Resources Dashboard'],
        manual_parameters=[
            openapi.Parameter(
                'month',
                openapi.IN_QUERY,
                description='Filter by month (1-12), must be used with year',
                type=openapi.TYPE_INTEGER,
                enum=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                required=False
            ),
            openapi.Parameter(
                'year',
                openapi.IN_QUERY,
                description='Filter by year (YYYY), must be used with month',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="Task resources dashboard statistics",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'total_tasks': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total number of tasks with resources'),
                        'total_cost': openapi.Schema(type=openapi.TYPE_NUMBER, description='Total cost of all resources used in tasks')
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """Get task resources dashboard statistics"""
        # Get month and year filters
        month_filter = request.query_params.get('month', None)
        year_filter = request.query_params.get('year', None)
        
        # Filter tasks by month/year if provided
        tasks_queryset = Task.objects.filter(
            resources__isnull=False
        ).distinct()
        
        if month_filter and year_filter:
            month = int(month_filter)
            year = int(year_filter)
            first_day = date(year, month, 1)
            last_day = date(year, month, monthrange(year, month)[1])
            tasks_queryset = tasks_queryset.filter(
                task_date__gte=first_day,
                task_date__lte=last_day
            )
        
        # Get task IDs
        task_ids = list(tasks_queryset.values_list('id', flat=True))
        
        # Total tasks with resources
        total_tasks = len(task_ids)
        
        # Total cost of all resources
        if task_ids:
            total_cost = TaskResource.objects.filter(
                task_id__in=task_ids
            ).aggregate(
                total=Coalesce(Sum('total_cost'), 0)
            )['total'] or 0
        else:
            total_cost = 0
        
        data = {
            'total_tasks': total_tasks,
            'total_cost': float(total_cost)
        }
        
        serializer = TaskResourcesStatisticsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_id='task_resources_list',
        operation_summary="List All Tasks with Resources",
        operation_description="""
        Retrieve a list of all tasks that have resources, with detailed resource information.
        
        **What it returns:**
        - List of tasks with resources, each containing:
          * Task name
          * Employee name (who did the task)
          * Project name (for which project the task was done)
          * Client name (who was the client)
          * Task date (on which date the task was done)
          * Number of resources used
          * Grand Total of all resources in that task
          * Resource Breakdown (Resource Name, quantity, unit cost, total cost)
        
        **Search Options:**
        - search: Search by employee name, client name, project name, or task name (case-insensitive partial match)
        
        **Filtering Options:**
        - month: Filter by month (1-12) - must be used with year
        - year: Filter by year (YYYY) - must be used with month
        
        **Query Parameters:**
        - search (optional): Search by employee name, client name, project name, or task name
        - month (optional): Filter by month (1-12), must be used with year
        - year (optional): Filter by year (YYYY), must be used with month
        
        **Pagination:**
        Results are paginated (20 items per page by default) and sorted by task date (newest first).
        """,
        tags=['Task Resources Dashboard'],
        manual_parameters=[
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description='Search by employee name, client name, project name, or task name',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'month',
                openapi.IN_QUERY,
                description='Filter by month (1-12), must be used with year',
                type=openapi.TYPE_INTEGER,
                enum=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                required=False
            ),
            openapi.Parameter(
                'year',
                openapi.IN_QUERY,
                description='Filter by year (YYYY), must be used with month',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of tasks with resources",
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
        """List all tasks with resources"""
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='task_resources_retrieve',
        operation_summary="Get Task Resources Details",
        operation_description="""
        Retrieve detailed information about a specific task with all its resources.
        
        **What it returns:**
        - Complete task information with all resource details
        - Task name, employee name, project name, client name
        - Task date, number of resources, grand total
        - Resource breakdown with all resource details
        """,
        tags=['Task Resources Dashboard'],
        responses={
            200: TaskResourcesDashboardSerializer()
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """Get task resources details"""
        return super().retrieve(request, *args, **kwargs)
