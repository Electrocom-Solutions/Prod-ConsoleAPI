from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q, Sum, Count
from django.db.models.functions import Coalesce
from django.db import transaction
from django.http import FileResponse
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils.decorators import method_decorator
from urllib.parse import quote
from datetime import date, datetime, timedelta
from calendar import monthrange
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import os

from .models import Task, TaskResource, TaskAttachment
from .serializers import (
    TaskStatisticsSerializer,
    TaskListSerializer,
    TaskDetailSerializer,
    TaskCreateSerializer,
    BulkApproveSerializer,
    BulkDeleteSerializer,
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
        'project', 'project__tender', 'created_by', 'updated_by'
    ).prefetch_related('attachments', 'resources').all()
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
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
        
        # Search by employee name, project name, or tender name
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(employee__profile__user__first_name__icontains=search) |
                Q(employee__profile__user__last_name__icontains=search) |
                Q(employee__profile__user__username__icontains=search) |
                Q(project__name__icontains=search) |
                Q(project__tender__name__icontains=search) |
                Q(project__tender__reference_number__icontains=search)
            )
        
        # Filter by project
        project_filter = self.request.query_params.get('project', None)
        if project_filter:
            queryset = queryset.filter(project_id=project_filter)
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by approval_status
        approval_status_filter = self.request.query_params.get('approval_status', None)
        if approval_status_filter:
            queryset = queryset.filter(approval_status=approval_status_filter)
        
        # Date filter
        date_filter = self.request.query_params.get('date_filter', 'all').lower()
        start_date, end_date = self._get_date_range(date_filter)
        if date_filter != 'all' and start_date and end_date:
            queryset = queryset.filter(
                deadline__gte=start_date,
                deadline__lte=end_date
            )
        
        return queryset.order_by('-deadline', '-created_at')
    
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
        - `today`: Statistics for tasks with deadline = today
        - `this_week`: Statistics for tasks with deadline within the current week (Monday to Sunday)
        - `this_month`: Statistics for tasks with deadline within the current month
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
                deadline__gte=start_date,
                deadline__lte=end_date
            )
        
        # Calculate statistics
        # Total tasks
        total_tasks = tasks_queryset.count()
        
        # Pending approval (approval_status = pending)
        pending_approval = tasks_queryset.filter(approval_status=Task.ApprovalStatus.PENDING).count()
        
        # In Progress (status = In Progress)
        in_progress = tasks_queryset.filter(status=Task.Status.IN_PROGRESS).count()
        
        # Approved tasks (approval_status = approved)
        approved_tasks = tasks_queryset.filter(approval_status=Task.ApprovalStatus.APPROVED).count()
        
        # Total resource cost (sum of all TaskResource.total_cost for these tasks)
        try:
            # Get task IDs for resource cost calculation
            task_ids = list(tasks_queryset.values_list('id', flat=True))
            
            if task_ids:
                total_resource_cost_result = TaskResource.objects.filter(
                    task__in=task_ids
                ).aggregate(
                    total=Coalesce(Sum('total_cost'), 0)
                )
                total_resource_cost = total_resource_cost_result.get('total', 0) or 0
            else:
                total_resource_cost = 0
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error calculating total resource cost: {str(e)}")
            total_resource_cost = 0
        
        try:
            from decimal import Decimal
            
            # Ensure values are properly converted to Decimal
            # Handle Decimal types that might already be Decimal
            if isinstance(total_resource_cost, Decimal):
                total_resource_cost_decimal = total_resource_cost
            elif total_resource_cost is None:
                total_resource_cost_decimal = Decimal('0.00')
            else:
                try:
                    # Try to convert to float first, then to Decimal
                    total_resource_cost_float = float(total_resource_cost)
                    total_resource_cost_decimal = Decimal(str(total_resource_cost_float))
                except (ValueError, TypeError):
                    total_resource_cost_decimal = Decimal('0.00')
            
            data = {
                'total_tasks': int(total_tasks),
                'in_progress': int(in_progress),
                'pending_approval': int(pending_approval),
                'approved_tasks': int(approved_tasks),
                'total_resource_cost': total_resource_cost_decimal
            }
            
            serializer = TaskStatisticsSerializer(data=data)
            if not serializer.is_valid():
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Statistics serialization error: {serializer.errors}")
                return Response(
                    {'error': 'Serialization error', 'details': serializer.errors},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            error_msg = f"Error in task statistics: {str(e)}"
            error_traceback = traceback.format_exc()
            logger.error(error_msg)
            logger.error(error_traceback)
            
            from django.conf import settings
            error_response = {
                'error': 'Failed to fetch task statistics',
                'message': str(e)
            }
            if settings.DEBUG:
                error_response['traceback'] = error_traceback
                error_response['details'] = {
                    'total_tasks': total_tasks,
                    'total_minutes': total_minutes,
                    'total_timings': total_timings,
                    'total_resource_cost': str(total_resource_cost),
                    'task_ids_count': len(task_ids) if task_ids else 0
                }
            
            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_id='task_list',
        operation_summary="List All Tasks",
        operation_description="""
        Retrieve a list of all tasks with filtering and search options.
        
        **What it returns:**
        - List of tasks with basic information (task name, date, location, time taken, status)
        - Employee name, project name, and tender name for easy reference
        - Time taken in both minutes and hours
        
        **Search Options:**
        - search: Search by employee name (first name, last name, username), project name, or tender name/reference number (case-insensitive partial match)
        
        **Filtering Options:**
        - project: Filter by project ID
        - status: Filter by task status (Draft, In Progress, Completed, Canceled)
        - date_filter: Filter by date range (today, this_week, this_month, all)
          * today: Tasks with deadline = today
          * this_week: Tasks with deadline within the current week (Monday to Sunday)
          * this_month: Tasks with deadline within the current month
          * all: All tasks (no date filter) - this is the default
        
        **Query Parameters:**
        - search (optional): Search by employee name, project name, or tender name/reference number
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
                description='Search by employee name, project name, or tender name/reference number',
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
          * Project name and tender name
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
                # Get all valid tasks (no status restriction for approval)
                tasks_to_approve = Task.objects.filter(id__in=task_ids)
                
                approved_count = 0
                skipped_count = 0
                errors = []
                
                for task in tasks_to_approve:
                    try:
                        # Update only approval_status to approved (don't change task status)
                        task.approval_status = Task.ApprovalStatus.APPROVED
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
                
                # Count skipped tasks (tasks that don't exist or already approved)
                skipped_count = len(task_ids) - tasks_to_approve.count()
                
                # Note: We don't add "Tasks not found" to errors array because:
                # 1. It's already represented by skipped_count
                # 2. Missing tasks are expected (could be deleted by another user or stale selection)
                # 3. Errors array should only contain actual errors (database errors, permission errors, etc.)
                
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
        operation_id='task_bulk_delete',
        operation_summary="Delete Multiple Tasks",
        operation_description="""
        Delete multiple tasks from the system. This action is permanent and cannot be undone.
        
        **What it does:**
        - Accepts a list of task IDs
        - Deletes all selected tasks
        - Creates activity log entries for each deleted task
        - Returns the number of tasks deleted and any errors
        
        **Request Body:**
        ```json
        {
          "task_ids": [1, 2, 3, 4, 5]
        }
        ```
        
        **Warning:**
        Deleting tasks will also delete all associated attachments and resources.
        
        **Response:**
        Returns the number of tasks deleted and any errors encountered.
        
        **Use Case:**
        Use this endpoint when users select multiple tasks and click "Delete" button to delete them all at once.
        """,
        tags=['Task Management'],
        responses={
            200: openapi.Response(
                description="Tasks deleted successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'deleted_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of tasks deleted'),
                        'skipped_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of tasks skipped (not found)'),
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
    @action(detail=False, methods=['post'], url_path='bulk-delete')
    def bulk_delete(self, request):
        """Delete multiple tasks"""
        serializer = BulkDeleteSerializer(data=request.data)
        
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
                # Get all valid tasks
                tasks_to_delete = Task.objects.filter(id__in=task_ids)
                
                deleted_count = 0
                skipped_count = 0
                errors = []
                
                # Store task names before deletion for activity logs
                task_info = {task.id: task.task_name for task in tasks_to_delete}
                
                for task in tasks_to_delete:
                    try:
                        task_name = task_info[task.id]
                        task_id = task.id
                        
                        # Create activity log before deletion
                        ActivityLog.objects.create(
                            entity_type=ActivityLog.EntityType.TASK,
                            entity_id=task_id,
                            action=ActivityLog.Action.DELETED,
                            description=f"Task {task_name} deleted",
                            created_by=request.user
                        )
                        
                        # Delete the task (this will cascade delete attachments and resources)
                        task.delete()
                        deleted_count += 1
                    except Exception as e:
                        errors.append(f"Error deleting task {task.id}: {str(e)}")
                
                # Count skipped tasks (tasks that don't exist)
                skipped_count = len(task_ids) - tasks_to_delete.count()
                
                # Note: We don't add "Tasks not found" to errors array because:
                # 1. It's already represented by skipped_count
                # 2. Missing tasks are expected (could be deleted by another user or stale selection)
                # 3. Errors array should only contain actual errors (database errors, permission errors, etc.)
                
                return Response({
                    'deleted_count': deleted_count,
                    'skipped_count': skipped_count,
                    'errors': errors if errors else None
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            return Response(
                {'error': f'Error deleting tasks: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_id='task_create',
        operation_summary="Create New Task",
        operation_description="""
        Create a new task with all required and optional information.
        
        **Required Fields:**
        - project: ID of the project associated with this task
        - deadline: Task deadline/date (YYYY-MM-DD) - optional field
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
        
        # When employee marks task as completed, ensure approval_status remains Pending
        if not request.user.is_superuser and old_status != Task.Status.COMPLETED and new_status == Task.Status.COMPLETED:
            # Ensure approval_status remains Pending (employees cannot approve their own tasks)
            if instance.approval_status != Task.ApprovalStatus.PENDING:
                instance.approval_status = Task.ApprovalStatus.PENDING
                instance.save(update_fields=['approval_status'])
            
            employee_name = request.user.get_full_name() or request.user.username
            send_notification_to_owners(
                title="Task Completed",
                message=f"Employee {employee_name} has marked task '{instance.task_name}' as completed. Please review and approve.",
                notification_type="Task",
                created_by=request.user
            )
        
        # Create activity log
        ActivityLog.objects.create(
            entity_type=ActivityLog.EntityType.TASK,
            entity_id=instance.id,
            action=ActivityLog.Action.UPDATED,
            description=f"Task {instance.task_name} updated",
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
        operation_id='task_download_document',
        operation_summary="Download Task Document",
        operation_description="""
        Download a document attached to a task.
        
        **What it does:**
        - Returns the file for download
        - Validates that the document belongs to the specified task
        
        **Path Parameters:**
        - task_id: ID of the task
        - document_id: ID of the document to download
        
        **Response:**
        Returns the file for download.
        """,
        tags=['Task Management'],
        responses={
            200: openapi.Response(description="File download"),
            404: openapi.Response(description="Document not found")
        }
    )
    @action(detail=True, methods=['get'], url_path='download-document/(?P<document_id>[0-9]+)')
    def download_document(self, request, pk=None, document_id=None):
        """Download a document from a task"""
        try:
            task = self.get_object()
            document = TaskAttachment.objects.get(
                id=document_id,
                task_id=pk
            )
            
            if not document.file:
                return Response(
                    {'error': 'File not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Return file response
            return FileResponse(document.file.open(), as_attachment=True, filename=document.file.name.split('/')[-1])
            
        except TaskAttachment.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Error downloading document: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_id='task_preview_document',
        operation_summary="Preview Task Document",
        operation_description="""
        Preview a document attached to a task in the browser (inline display).
        
        **What it does:**
        - Validates that the document belongs to the specified task
        - Retrieves the file associated with that document
        - Returns the file with inline content disposition for browser preview
        
        **Use Case:**
        Use this endpoint to display PDFs/images in an iframe or embed tag for preview purposes.
        The file is served with proper headers for inline display and iframe embedding.
        
        **Path Parameters:**
        - task_id: ID of the task
        - document_id: ID of the document to preview
        """,
        tags=['Task Management'],
        responses={
            200: openapi.Response(
                description="File preview (inline)",
                schema=openapi.Schema(type=openapi.TYPE_FILE)
            ),
            404: openapi.Response(description="Document not found")
        }
    )
    @method_decorator(xframe_options_exempt)
    @action(detail=True, methods=['get'], url_path='preview-document/(?P<document_id>[0-9]+)')
    def preview_document(self, request, pk=None, document_id=None):
        """Preview a document from a task (inline display for iframe)"""
        try:
            task = self.get_object()
            document = TaskAttachment.objects.get(
                id=document_id,
                task_id=pk
            )
            
            if not document.file:
                return Response(
                    {'error': 'File not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Determine content type based on file extension
            file_name = document.file.name.lower()
            if file_name.endswith('.pdf'):
                content_type = 'application/pdf'
            elif file_name.endswith(('.jpg', '.jpeg')):
                content_type = 'image/jpeg'
            elif file_name.endswith('.png'):
                content_type = 'image/png'
            elif file_name.endswith('.gif'):
                content_type = 'image/gif'
            elif file_name.endswith('.webp'):
                content_type = 'image/webp'
            elif file_name.endswith(('.doc', '.docx')):
                content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            else:
                content_type = 'application/octet-stream'
            
            # Get filename
            filename = document.file.name.split('/')[-1]
            
            # Create file response with inline disposition for preview
            response = FileResponse(
                document.file.open('rb'),
                content_type=content_type
            )
            # Use inline instead of attachment for preview
            response['Content-Disposition'] = f'inline; filename="{quote(filename)}"'
            # Remove X-Frame-Options header to allow iframe embedding
            try:
                del response['X-Frame-Options']
            except KeyError:
                pass  # Header doesn't exist, which is fine
            # Add CORS headers if needed
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'GET'
            response['Access-Control-Allow-Headers'] = 'Content-Type'
            return response
            
        except TaskAttachment.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Error previewing document: {str(e)}'},
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
    
    @swagger_auto_schema(
        operation_id='task_approve',
        operation_summary="Approve Task",
        operation_description="""
        Approve a single task (change status from Draft to In Progress).
        
        **What it does:**
        - Updates task status from "Draft" to "In Progress"
        - Creates activity log entry
        - Sends notification to employee if task is assigned
        
        **Response:**
        Returns the updated task with all details.
        """,
        tags=['Task Management'],
        responses={
            200: openapi.Response(
                description="Task approved successfully",
                schema=TaskDetailSerializer()
            ),
            400: openapi.Response(
                description="Task cannot be approved (not in Draft status)",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        }
    )
    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """Approve a single task"""
        try:
            task = self.get_object()
            
            # Check if task is in Draft status
            if task.status != Task.Status.DRAFT:
                return Response(
                    {'error': f'Task cannot be approved. Current status: {task.status}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update task status to In Progress (approved)
            task.status = Task.Status.IN_PROGRESS
            task.approval_status = Task.ApprovalStatus.APPROVED
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
            
            # Return updated task
            serializer = TaskDetailSerializer(task, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Error approving task: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_id='task_reject',
        operation_summary="Reject Task",
        operation_description="""
        Reject a single task (change status from Draft to Canceled).
        
        **What it does:**
        - Updates task status from "Draft" to "Canceled"
        - Creates activity log entry with rejection reason
        - Sends notification to employee if task is assigned
        
        **Request Body:**
        ```json
        {
          "reason": "Optional rejection reason"
        }
        ```
        
        **Response:**
        Returns the updated task with all details.
        """,
        tags=['Task Management'],
        responses={
            200: openapi.Response(
                description="Task rejected successfully",
                schema=TaskDetailSerializer()
            ),
            400: openapi.Response(
                description="Task cannot be rejected (not in Draft status)",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        }
    )
    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """Reject a single task"""
        try:
            task = self.get_object()
            
            # Check if task is in Draft status
            if task.status != Task.Status.DRAFT:
                return Response(
                    {'error': f'Task cannot be rejected. Current status: {task.status}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get rejection reason
            reason = request.data.get('reason', 'Task rejected')
            
            # Update task status to Canceled (rejected)
            task.status = Task.Status.CANCELED
            task.approval_status = Task.ApprovalStatus.REJECTED
            task.updated_by = request.user
            task.save()
            
            # Create activity log
            ActivityLog.objects.create(
                entity_type=ActivityLog.EntityType.TASK,
                entity_id=task.id,
                action=ActivityLog.Action.UPDATED,
                description=f"Task {task.task_name} rejected: {reason}",
                created_by=request.user
            )
            
            # Notify employee when task is rejected
            if task.employee and task.employee.profile and task.employee.profile.user:
                employee_user = task.employee.profile.user
                send_notification_to_user(
                    user=employee_user,
                    title="Task Rejected",
                    message=f"Your task '{task.task_name}' has been rejected. Reason: {reason}",
                    notification_type="Task",
                    created_by=request.user
                )
            
            # Return updated task
            serializer = TaskDetailSerializer(task, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Error rejecting task: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_id='task_update_resource',
        operation_summary="Update Task Resource",
        operation_description="""
        Update a resource attached to a task. This is used to update unit costs and quantities.
        
        **What it does:**
        - Updates resource quantity, unit_cost, and recalculates total_cost
        - Creates activity log entry
        - Returns the updated resource
        
        **Request Fields:**
        - quantity (optional): Updated quantity
        - unit_cost (optional): Updated unit cost
        - total_cost (optional): Updated total cost (will be recalculated if not provided)
        
        **Response:**
        Returns the updated resource record.
        """,
        tags=['Task Management'],
        responses={
            200: openapi.Response(
                description="Resource updated successfully",
                schema=TaskResourceCreateSerializer()
            ),
            404: openapi.Response(description="Resource not found")
        }
    )
    @action(detail=True, methods=['patch'], url_path='update-resource/(?P<resource_id>[0-9]+)')
    def update_resource(self, request, pk=None, resource_id=None):
        """Update a resource attached to a task"""
        try:
            task = self.get_object()
            resource = TaskResource.objects.get(
                id=resource_id,
                task_id=pk
            )
            
            # Update resource fields
            quantity = request.data.get('quantity', resource.quantity)
            unit_cost = request.data.get('unit_cost', resource.unit_cost)
            total_cost = request.data.get('total_cost')
            
            # Calculate total_cost if not provided
            if total_cost is None:
                total_cost = float(quantity) * float(unit_cost)
            
            resource.quantity = quantity
            resource.unit_cost = unit_cost
            resource.total_cost = total_cost
            resource.updated_by = request.user
            resource.save()
            
            # Create activity log
            ActivityLog.objects.create(
                entity_type=ActivityLog.EntityType.TASK,
                entity_id=task.id,
                action=ActivityLog.Action.UPDATED,
                description=f"Resource {resource.resource_name} updated in task {task.task_name}",
                created_by=request.user
            )
            
            serializer = TaskResourceCreateSerializer(resource, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except TaskResource.DoesNotExist:
            return Response(
                {'error': 'Resource not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Error updating resource: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TaskResourcesDashboardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Task Resources Dashboard APIs
    """
    queryset = Task.objects.select_related(
        'employee', 'employee__profile', 'employee__profile__user',
        'project', 'project__tender', 'created_by', 'updated_by'
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
            try:
                # Filter by specific month and year
                month = int(month_filter)
                year = int(year_filter)
                
                # Validate month and year
                if month < 1 or month > 12:
                    return queryset.none()
                if year < 1900 or year > 2100:
                    return queryset.none()
                
                # Get first and last day of the month
                first_day = date(year, month, 1)
                last_day = date(year, month, monthrange(year, month)[1])
                queryset = queryset.filter(
                    deadline__gte=first_day,
                    deadline__lte=last_day
                )
            except (ValueError, TypeError) as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Invalid month/year filter: {month_filter}/{year_filter}, error: {str(e)}")
                return queryset.none()
        
        # Search by employee, tender, project, task name
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(task_name__icontains=search) |
                Q(employee__profile__user__first_name__icontains=search) |
                Q(employee__profile__user__last_name__icontains=search) |
                Q(employee__profile__user__username__icontains=search) |
                Q(project__name__icontains=search) |
                Q(project__tender__name__icontains=search) |
                Q(project__tender__reference_number__icontains=search)
            )
        
        return queryset.order_by('-deadline', '-created_at')
    
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
                        'total_resources': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total count of resources across all tasks'),
                        'total_cost': openapi.Schema(type=openapi.TYPE_NUMBER, description='Total cost of all resources used in tasks'),
                        'avg_cost_per_task': openapi.Schema(type=openapi.TYPE_NUMBER, description='Average cost per task')
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
                deadline__gte=first_day,
                deadline__lte=last_day
            )
        
        # Get task IDs
        task_ids = list(tasks_queryset.values_list('id', flat=True))
        
        # Total tasks with resources
        total_tasks = len(task_ids)
        
        # Total resources count and total cost
        if task_ids:
            resource_stats = TaskResource.objects.filter(
                task__in=task_ids
            ).aggregate(
                total_count=Count('id'),
                total_cost=Coalesce(Sum('total_cost'), 0)
            )
            total_resources = resource_stats['total_count'] or 0
            total_cost = resource_stats['total_cost'] or 0
        else:
            total_resources = 0
            total_cost = 0
        
        # Calculate average cost per task
        avg_cost_per_task = float(total_cost) / total_tasks if total_tasks > 0 else 0
        
        data = {
            'total_tasks': total_tasks,
            'total_resources': total_resources,
            'total_cost': float(total_cost),
            'avg_cost_per_task': avg_cost_per_task
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
          * Tender name (which tender the project belongs to)
          * Task date (on which date the task was done)
          * Number of resources used
          * Grand Total of all resources in that task
          * Resource Breakdown (Resource Name, quantity, unit cost, total cost)
        
        **Search Options:**
        - search: Search by employee name, tender name/reference number, project name, or task name (case-insensitive partial match)
        
        **Filtering Options:**
        - month: Filter by month (1-12) - must be used with year
        - year: Filter by year (YYYY) - must be used with month
        
        **Query Parameters:**
        - search (optional): Search by employee name, tender name/reference number, project name, or task name
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
                description='Search by employee name, tender name/reference number, project name, or task name',
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
        - Task name, employee name, project name, tender name
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
