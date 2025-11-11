"""
Views for Notifications app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Notification, EmailTemplate
from .serializers import (
    NotificationListSerializer,
    NotificationDetailSerializer,
    NotificationMarkReadSerializer,
    BulkMarkReadSerializer,
    NotificationCreateSerializer,
    NotificationStatisticsSerializer,
    EmailTemplateListSerializer,
    EmailTemplateDetailSerializer,
    EmailTemplateCreateUpdateSerializer,
    EmailTemplateSendSerializer
)


class NotificationViewSet(viewsets.ModelViewSet):
    """
    Notification Management APIs
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return notifications for the current user with search and filters"""
        if not self.request.user.is_authenticated:
            # During schema generation, return empty queryset
            return Notification.objects.none()
        
        # Check if user wants to see notifications they sent (owner view)
        show_sent_by_me = self.request.query_params.get('show_sent_by_me', None)
        show_scheduled = self.request.query_params.get('show_scheduled', None)
        
        if show_sent_by_me and show_sent_by_me.lower() == 'true':
            # Show notifications sent by the current user (owner view)
            # This shows all notifications created by the owner, regardless of recipient
            queryset = Notification.objects.filter(
                created_by=self.request.user
            ).select_related('created_by', 'recipient')
            
            # Filter by scheduled status
            if show_scheduled and show_scheduled.lower() == 'true':
                # Show scheduled notifications (not yet sent)
                # Group by title, message, scheduled_at, and created_by to avoid duplicates
                queryset = queryset.filter(sent_at__isnull=True, scheduled_at__isnull=False)
                # Use distinct with specific fields to get unique scheduled notifications
                # Note: distinct() with field names requires ordering by those fields first (PostgreSQL requirement)
                # We order by scheduled_at first to get the earliest notification of each group, then by other fields for distinct
                queryset = queryset.order_by('scheduled_at', 'title', 'message', 'created_by').distinct('scheduled_at', 'title', 'message', 'created_by')
            else:
                # Show sent notifications (default behavior)
                queryset = queryset.filter(sent_at__isnull=False)
        else:
            # Default: Show notifications received by the current user
            queryset = Notification.objects.filter(
                recipient=self.request.user
            ).select_related('created_by', 'recipient')
            
            # Filter by scheduled status
            if show_scheduled and show_scheduled.lower() == 'true':
                # Show scheduled notifications (not yet sent)
                queryset = queryset.filter(sent_at__isnull=True, scheduled_at__isnull=False)
            else:
                # Show sent notifications (default behavior)
                queryset = queryset.filter(sent_at__isnull=False)
        
        # Search by title or message
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(message__icontains=search)
            )
        
        # Filter by type
        type_filter = self.request.query_params.get('type', None)
        if type_filter:
            queryset = queryset.filter(type=type_filter)
        
        # Filter by read status (only for sent notifications, not scheduled, and only for received notifications)
        is_read_filter = self.request.query_params.get('is_read', None)
        if is_read_filter is not None and not (show_scheduled and show_scheduled.lower() == 'true') and not (show_sent_by_me and show_sent_by_me.lower() == 'true'):
            is_read = is_read_filter.lower() == 'true'
            queryset = queryset.filter(is_read=is_read)
        
        # Order by scheduled_at for scheduled notifications, created_at for sent notifications
        # Note: For scheduled notifications with distinct(), we already ordered in the distinct() call above
        if show_scheduled and show_scheduled.lower() == 'true' and show_sent_by_me and show_sent_by_me.lower() == 'true':
            # Already ordered by distinct fields, but reorder by scheduled_at for final display
            # We need to re-query to avoid ordering conflict with distinct
            from django.db.models import Min
            # Get unique scheduled notifications grouped by title, message, scheduled_at, created_by
            # Then order by scheduled_at
            return queryset.order_by('scheduled_at')
        elif show_scheduled and show_scheduled.lower() == 'true':
            return queryset.order_by('scheduled_at')
        return queryset.order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return NotificationListSerializer
        elif self.action in ['retrieve']:
            return NotificationDetailSerializer
        elif self.action in ['create']:
            return NotificationCreateSerializer
        elif self.action in ['mark_read']:
            return NotificationMarkReadSerializer
        elif self.action in ['bulk_mark_read']:
            return BulkMarkReadSerializer
        return NotificationListSerializer
    
    @swagger_auto_schema(
        operation_id='notification_list',
        operation_summary="Get All Notifications for Current User",
        operation_description="""
        Retrieve all notifications for the currently authenticated user.
        
        **What it returns:**
        - List of all notifications for the current user
        - Includes read/unread status
        - Includes scheduled and sent timestamps if applicable
        - Sorted by creation date (newest first)
        
        **Search Options:**
        - search: Search by title or message (case-insensitive partial match)
        
        **Filtering Options:**
        - type: Filter by notification type (Task, AMC, Tender, Payroll, System, Other)
        - is_read: Filter by read status (true/false) - only for sent notifications and received notifications
        - show_scheduled: Show scheduled notifications instead of sent ones (true/false)
        - show_sent_by_me: Show notifications sent by the current user (owner view) (true/false)
        
        **Query Parameters:**
        - search (optional): Search by title or message
        - type (optional): Filter by notification type
        - is_read (optional): Filter by read status (true/false) - only for sent notifications and received notifications
        - show_scheduled (optional): Set to 'true' to show scheduled notifications instead of sent ones
        - show_sent_by_me (optional): Set to 'true' to show notifications sent by the current user (owner view)
        
        **Note:**
        Only notifications for the authenticated user are returned.
        
        **Pagination:**
        Results are paginated (20 items per page by default) and sorted by creation date (newest first).
        """,
        tags=['Notifications'],
        manual_parameters=[
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description='Search by title or message',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'type',
                openapi.IN_QUERY,
                description='Filter by notification type',
                type=openapi.TYPE_STRING,
                enum=['Task', 'AMC', 'Tender', 'Payroll', 'System', 'Other'],
                required=False
            ),
            openapi.Parameter(
                'is_read',
                openapi.IN_QUERY,
                description='Filter by read status',
                type=openapi.TYPE_BOOLEAN,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of notifications",
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
        """Get all notifications for the current user"""
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='notification_statistics',
        operation_summary="Get Notification Statistics",
        operation_description="""
        Retrieve statistics for notifications for the currently authenticated user.
        
        **What it returns:**
        - total_notifications: Total number of notifications for the current user
        - unread_count: Number of unread notifications
        - read_count: Number of read notifications
        
        **Note:**
        Only statistics for the authenticated user are returned.
        
        **Use Case:**
        Use this endpoint to populate dashboard tiles showing notification metrics.
        """,
        tags=['Notifications'],
        responses={
            200: openapi.Response(
                description="Notification statistics",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'total_notifications': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total number of notifications'),
                        'unread_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of unread notifications'),
                        'read_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of read notifications')
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """Get notification statistics for current user"""
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Get statistics for current user
        notifications = Notification.objects.filter(recipient=request.user)
        
        total_notifications = notifications.count()
        unread_count = notifications.filter(is_read=False).count()
        read_count = notifications.filter(is_read=True).count()
        
        data = {
            'total_notifications': total_notifications,
            'unread_count': unread_count,
            'read_count': read_count
        }
        
        serializer = NotificationStatisticsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_id='notification_retrieve',
        operation_summary="Get Notification Details",
        operation_description="""
        Retrieve detailed information about a specific notification.
        
        **Note:**
        Users can only retrieve their own notifications.
        """,
        tags=['Notifications'],
        responses={
            200: NotificationDetailSerializer(),
            404: openapi.Response(description="Notification not found")
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """Get notification details"""
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='notification_create',
        operation_summary="Create Notification for All Employees (Owner Only)",
        operation_description="""
        Create a notification that will be sent to all employees. Only superadmins (owners) can use this endpoint.
        
        **Required Fields:**
        - title: Notification title
        - message: Notification message
        - type: Notification type (Task, AMC, Tender, Payroll, System, Other)
        
        **Optional Fields:**
        - channel: Notification channel (In-App, Email, Push) - default: In-App
        - scheduled_at: Schedule notification for a specific date and time (YYYY-MM-DD HH:MM:SS format)
          * If not provided, notification is sent immediately
          * If provided and in the future, notification will be scheduled for that time
          * If provided and in the past, notification is sent immediately
        
        **Behavior:**
        - Creates a notification for each employee (user linked to Employee model)
        - If scheduled_at is provided and in the future, notifications are created but not sent yet
        - If scheduled_at is not provided or in the past, notifications are sent immediately
        
        **Response:**
        Returns the first notification created (as a sample). All employee notifications are created in the background.
        """,
        tags=['Notifications'],
        request_body=NotificationCreateSerializer,
        responses={
            201: openapi.Response(
                description="Notification created successfully",
                schema=NotificationCreateSerializer()
            ),
            403: openapi.Response(description="Only superadmins can create notifications for employees")
        }
    )
    def create(self, request, *args, **kwargs):
        """Create notification for all employees (owner only)"""
        # Check if user is superadmin
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only superadmins (owners) can create notifications for employees'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notification = serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @swagger_auto_schema(
        operation_id='notification_mark_read',
        operation_summary="Mark Notification as Read",
        operation_description="""
        Mark a single notification as read.
        
        **What it does:**
        - Updates the notification's is_read status to True
        - Returns the updated notification
        
        **Note:**
        Users can only mark their own notifications as read.
        
        **Response:**
        Returns the updated notification with is_read=True.
        """,
        tags=['Notifications'],
        responses={
            200: openapi.Response(
                description="Notification marked as read successfully",
                schema=NotificationDetailSerializer()
            ),
            404: openapi.Response(description="Notification not found")
        }
    )
    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()
        
        # Ensure user can only mark their own notifications
        if notification.recipient != request.user:
            return Response(
                {'error': 'You can only mark your own notifications as read'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        notification.is_read = True
        notification.save()
        
        serializer = NotificationDetailSerializer(notification, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_id='notification_bulk_mark_read',
        operation_summary="Bulk Mark Notifications as Read",
        operation_description="""
        Mark multiple notifications as read in bulk.
        
        **What it does:**
        - Accepts a list of notification IDs OR a mark_all flag
        - Updates all selected notifications' is_read status to True
        - Returns the number of notifications updated
        
        **Request Body Options:**
        
        Option 1: Mark specific notifications
        ```json
        {
          "notification_ids": [1, 2, 3, 4, 5],
          "mark_all": false
        }
        ```
        
        Option 2: Mark all notifications for current user
        ```json
        {
          "mark_all": true
        }
        ```
        
        **Required Fields:**
        - Either notification_ids (list) OR mark_all (boolean) must be provided
        
        **Validation:**
        - Users can only mark their own notifications as read
        - Invalid notification IDs are skipped
        
        **Response:**
        Returns the number of notifications marked as read and any errors encountered.
        """,
        tags=['Notifications'],
        request_body=BulkMarkReadSerializer,
        responses={
            200: openapi.Response(
                description="Notifications marked as read successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'marked_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of notifications marked as read'),
                        'skipped_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of notifications skipped (not found or not owned by user)'),
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
    @action(detail=False, methods=['post'], url_path='bulk-mark-read')
    def bulk_mark_read(self, request):
        """Mark multiple notifications as read"""
        serializer = BulkMarkReadSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        mark_all = serializer.validated_data.get('mark_all', False)
        notification_ids = serializer.validated_data.get('notification_ids', [])
        
        if mark_all:
            # Mark all notifications for current user as read
            updated_count = Notification.objects.filter(
                recipient=request.user,
                is_read=False
            ).update(is_read=True)
            
            return Response({
                'marked_count': updated_count,
                'skipped_count': 0,
                'errors': None
            }, status=status.HTTP_200_OK)
        
        elif notification_ids:
            # Mark specific notifications as read
            notifications = Notification.objects.filter(
                id__in=notification_ids,
                recipient=request.user  # Ensure user can only mark their own notifications
            )
            
            marked_count = notifications.update(is_read=True)
            skipped_count = len(notification_ids) - marked_count
            
            return Response({
                'marked_count': marked_count,
                'skipped_count': skipped_count,
                'errors': None if skipped_count == 0 else [f'Skipped {skipped_count} notification(s) that were not found or not owned by you']
            }, status=status.HTTP_200_OK)
        
        else:
            return Response(
                {'error': 'Either notification_ids or mark_all must be provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @swagger_auto_schema(
        operation_id='notification_cancel_scheduled',
        operation_summary="Cancel Scheduled Notification",
        operation_description="""
        Cancel a scheduled notification by deleting all notifications with the same title, message, scheduled_at, and created_by.
        
        **What it does:**
        - Finds all scheduled notifications matching the given notification's title, message, scheduled_at, and created_by
        - Deletes all matching scheduled notifications (not yet sent)
        - Returns the count of notifications cancelled
        
        **Note:**
        Only the user who created the scheduled notification can cancel it.
        """,
        tags=['Notifications'],
        responses={
            200: openapi.Response(
                description="Scheduled notification cancelled successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'cancelled_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of notifications cancelled'),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message')
                    }
                )
            ),
            404: openapi.Response(description="Notification not found"),
            403: openapi.Response(description="You can only cancel notifications you created")
        }
    )
    @action(detail=True, methods=['post'], url_path='cancel-scheduled')
    def cancel_scheduled(self, request, pk=None):
        """Cancel a scheduled notification"""
        from django.db import transaction
        from django.shortcuts import get_object_or_404
        
        # Get the notification directly (bypass get_queryset which may filter it out due to distinct)
        notification = get_object_or_404(Notification, pk=pk)
        
        # Check if user created this notification
        if notification.created_by != request.user:
            return Response(
                {'error': 'You can only cancel notifications you created'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if notification is scheduled (not yet sent)
        if not notification.scheduled_at or notification.sent_at:
            return Response(
                {'error': 'This notification is not scheduled or has already been sent'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Find all matching scheduled notifications
                matching_notifications = Notification.objects.filter(
                    title=notification.title,
                    message=notification.message,
                    scheduled_at=notification.scheduled_at,
                    created_by=notification.created_by,
                    sent_at__isnull=True,
                    scheduled_at__isnull=False
                )
                
                cancelled_count = matching_notifications.count()
                
                # Delete all matching scheduled notifications
                matching_notifications.delete()
                
                return Response({
                    'cancelled_count': cancelled_count,
                    'message': f'Successfully cancelled {cancelled_count} scheduled notification(s)'
                }, status=status.HTTP_200_OK)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error cancelling scheduled notification: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Failed to cancel scheduled notification: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_id='notification_bulk_delete',
        operation_summary="Bulk Delete Notifications",
        operation_description="""
        Delete multiple notifications at once.
        
        **What it does:**
        - Deletes notifications by their IDs
        - For owners: Can delete notifications they created (sent notifications)
        - For regular users: Can only delete notifications they received
        
        **Request Body:**
        - notification_ids: List of notification IDs to delete
        
        **Response:**
        Returns count of deleted notifications and any errors.
        """,
        tags=['Notifications'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'notification_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_INTEGER),
                    description='List of notification IDs to delete'
                )
            },
            required=['notification_ids']
        ),
        responses={
            200: openapi.Response(
                description="Notifications deleted successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'deleted_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of notifications deleted'),
                        'skipped_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of notifications skipped'),
                        'errors': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING), description='List of error messages')
                    }
                )
            ),
            400: openapi.Response(description="Invalid request data")
        }
    )
    @action(detail=False, methods=['post'], url_path='bulk-delete')
    def bulk_delete(self, request):
        """Bulk delete notifications"""
        notification_ids = request.data.get('notification_ids', [])
        
        if not notification_ids or not isinstance(notification_ids, list):
            return Response(
                {'error': 'notification_ids must be a non-empty list'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all notifications that the user can delete
        # Owners can delete notifications they created, regular users can delete notifications they received
        if request.user.is_superuser:
            # Owner: can delete notifications they created
            notifications = Notification.objects.filter(
                id__in=notification_ids,
                created_by=request.user
            )
        else:
            # Regular user: can only delete notifications they received
            notifications = Notification.objects.filter(
                id__in=notification_ids,
                recipient=request.user
            )
        
        deleted_count = notifications.count()
        skipped_count = len(notification_ids) - deleted_count
        
        # Delete the notifications
        notifications.delete()
        
        errors = None
        if skipped_count > 0:
            errors = [f'Skipped {skipped_count} notification(s) that were not found or you do not have permission to delete']
        
        return Response({
            'deleted_count': deleted_count,
            'skipped_count': skipped_count,
            'errors': errors
        }, status=status.HTTP_200_OK)
    
    def destroy(self, request, *args, **kwargs):
        """Delete a notification"""
        from django.shortcuts import get_object_or_404
        
        notification = get_object_or_404(Notification, pk=kwargs.get('pk'))
        
        # Owners can delete notifications they created (for sent notifications view)
        # Regular users can only delete notifications they received
        if request.user.is_superuser:
            # Owner: can delete notifications they created
            if notification.created_by != request.user:
                return Response(
                    {'error': 'You can only delete notifications you created'},
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            # Regular user: can only delete notifications they received
            if notification.recipient != request.user:
                return Response(
                    {'error': 'You can only delete your own notifications'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        notification.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EmailTemplateViewSet(viewsets.ModelViewSet):
    """
    Email Template Management APIs
    """
    permission_classes = [IsAuthenticated]
    queryset = EmailTemplate.objects.select_related('created_by', 'updated_by').all()
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return EmailTemplateListSerializer
        elif self.action in ['retrieve']:
            return EmailTemplateDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return EmailTemplateCreateUpdateSerializer
        elif self.action in ['send_email']:
            return EmailTemplateSendSerializer
        return EmailTemplateListSerializer
    
    def get_queryset(self):
        """Return email templates with search functionality"""
        queryset = super().get_queryset()
        
        # Search by template name or subject
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(subject__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    @swagger_auto_schema(
        operation_id='email_template_list',
        operation_summary="Get All Email Templates",
        operation_description="""
        Retrieve a list of all email templates with search functionality.
        
        **What it returns:**
        - List of email templates with basic information (name, subject, created date)
        
        **Search Options:**
        - search: Search by template name or subject (case-insensitive partial match)
        
        **Query Parameters:**
        - search (optional): Search by template name or subject
        
        **Pagination:**
        Results are paginated (20 items per page by default) and sorted by creation date (newest first).
        """,
        tags=['Email Template Dashboard'],
        manual_parameters=[
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description='Search by template name',
                type=openapi.TYPE_STRING,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of email templates",
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
        """Get all email templates with search"""
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='email_template_retrieve',
        operation_summary="Get Email Template Details",
        operation_description="""
        Retrieve detailed information about a specific email template.
        
        **What it returns:**
        - Complete template information including name, subject, body (HTML), and placeholders
        """,
        tags=['Email Template Dashboard'],
        responses={
            200: EmailTemplateDetailSerializer(),
            404: openapi.Response(description="Email template not found")
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """Get email template details"""
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='email_template_create',
        operation_summary="Create Email Template",
        operation_description="""
        Create a new email template.
        
        **Required Fields:**
        - name: Template Name
        - subject: Email Subject
        - body: Email Body (HTML)
        
        **Optional Fields:**
        - placeholders: Documentation of placeholders used in the template (e.g., "{{name}}, {{date}}")
        
        **Placeholders:**
        - Placeholders in the HTML body should be enclosed in double curly braces: {{placeholder_name}}
        - Example: "Hello {{name}}, your appointment is on {{date}}"
        - When sending emails, provide placeholder_values to replace these placeholders
        
        **Response:**
        Returns the created email template.
        """,
        tags=['Email Template Dashboard'],
        request_body=EmailTemplateCreateUpdateSerializer,
        responses={
            201: openapi.Response(
                description="Email template created successfully",
                schema=EmailTemplateCreateUpdateSerializer()
            )
        }
    )
    def create(self, request, *args, **kwargs):
        """Create a new email template"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @swagger_auto_schema(
        operation_id='email_template_update',
        operation_summary="Update Email Template",
        operation_description="""
        Update an existing email template. All fields are optional - only provided fields will be updated.
        
        **Fields:**
        Same as create endpoint - all fields are optional for update.
        
        **Response:**
        Returns the updated email template.
        """,
        tags=['Email Template Dashboard'],
        request_body=EmailTemplateCreateUpdateSerializer,
        responses={
            200: openapi.Response(
                description="Email template updated successfully",
                schema=EmailTemplateCreateUpdateSerializer()
            )
        }
    )
    def update(self, request, *args, **kwargs):
        """Update email template information"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_id='email_template_partial_update',
        operation_summary="Partial Update Email Template",
        operation_description="""
        Partially update an email template's information. Only provided fields will be updated.
        """,
        tags=['Email Template Dashboard'],
        request_body=EmailTemplateCreateUpdateSerializer,
        responses={
            200: openapi.Response(
                description="Email template partially updated successfully",
                schema=EmailTemplateCreateUpdateSerializer()
            )
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """Partially update email template information"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='email_template_delete',
        operation_summary="Delete Email Template",
        operation_description="""
        Delete an email template from the system. This action is permanent and cannot be undone.
        """,
        tags=['Email Template Dashboard'],
        responses={
            204: openapi.Response(description="Email template deleted successfully"),
            404: openapi.Response(description="Email template not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        """Delete an email template"""
        return super().destroy(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='email_template_send',
        operation_summary="Send Email Using Template",
        operation_description="""
        Send an email using the template to specified recipients.
        
        **Request Body:**
        - recipients: Comma-separated email addresses (e.g., "user1@example.com, user2@example.com")
        - scheduled_at (optional): Schedule email for a specific date and time (YYYY-MM-DD HH:MM:SS format)
          * If not provided, email is sent immediately
          * If provided and in the future, email will be scheduled for that time
          * If provided and in the past, email is sent immediately
        - placeholder_values (optional): Dictionary of placeholder values to replace in the email body
          * Example: {"name": "John", "date": "2025-01-01"}
          * These values will replace {{name}} and {{date}} in the email body
        
        **Behavior:**
        - Replaces placeholders in the email body with provided values
        - If scheduled_at is provided and in the future, email is scheduled for that time
        - If scheduled_at is not provided or in the past, email is sent immediately
        
        **Response:**
        Returns a summary of the email sending operation, including number of emails sent/scheduled.
        """,
        tags=['Email Template Dashboard'],
        request_body=EmailTemplateSendSerializer,
        responses={
            200: openapi.Response(
                description="Email sent/scheduled successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, description='Status: "sent" or "scheduled"'),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message'),
                        'recipients_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of recipients'),
                        'scheduled_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, description='Scheduled time if scheduled', nullable=True),
                        'sent_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, description='Sent time if sent immediately', nullable=True)
                    }
                )
            ),
            400: openapi.Response(description="Invalid request data"),
            404: openapi.Response(description="Email template not found")
        }
    )
    @action(detail=True, methods=['post'], url_path='send')
    def send_email(self, request, pk=None):
        """Send email using template"""
        from django.core.mail import send_mail
        from django.conf import settings
        import logging
        
        logger = logging.getLogger(__name__)
        
        template = self.get_object()
        serializer = EmailTemplateSendSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        recipients = serializer.validated_data['recipients']
        scheduled_at = serializer.validated_data.get('scheduled_at', None)
        placeholder_values = serializer.validated_data.get('placeholder_values', {})
        
        # Replace placeholders in subject and body
        subject = template.subject
        body = template.body
        
        # Replace placeholders with values
        for key, value in placeholder_values.items():
            placeholder = f"{{{{{key}}}}}"
            subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))
        
        # Determine if email should be sent immediately or scheduled
        current_time = timezone.now()
        import pytz
        
        # Log for debugging
        logger.info(f"Email send request - scheduled_at: {scheduled_at}, current_time: {current_time}, recipients_count: {len(recipients)}")
        
        # Handle timezone conversion for scheduled_at
        send_immediately = False
        if scheduled_at is None:
            send_immediately = True
        else:
            # Ensure scheduled_at is timezone-aware
            if timezone.is_naive(scheduled_at):
                kolkata_tz = pytz.timezone('Asia/Kolkata')
                scheduled_at = kolkata_tz.localize(scheduled_at)
                logger.info(f"Converted timezone-naive datetime to Asia/Kolkata: {scheduled_at}")
            
            # Convert to UTC for comparison and Celery
            scheduled_at_utc = scheduled_at.astimezone(pytz.UTC)
            current_time_utc = current_time.astimezone(pytz.UTC) if timezone.is_aware(current_time) else pytz.UTC.localize(current_time)
            
            # Check if scheduled time is in the past or present
            if scheduled_at_utc <= current_time_utc:
                logger.info(f"Scheduled time {scheduled_at_utc} is not in the future. Sending immediately.")
                send_immediately = True
        
        if send_immediately:
            logger.info("Sending email immediately")
            # Check if email backend is configured
            if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
                logger.warning("Email backend is set to console - emails will only be printed to console, not actually sent!")
            
            # Send email immediately
            try:
                # Send email to all recipients
                email_sent_count = 0
                errors = []
                
                # Check if email settings are configured
                from_email = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
                if not from_email:
                    return Response(
                        {'error': 'Email configuration is missing. Please configure DEFAULT_FROM_EMAIL or EMAIL_HOST_USER in settings.'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                
                for recipient_email in recipients:
                    try:
                        send_mail(
                            subject=subject,
                            message=body,  # Plain text fallback
                            from_email=from_email,
                            recipient_list=[recipient_email],
                            html_message=body,  # HTML content
                            fail_silently=False,
                        )
                        email_sent_count += 1
                        logger.info(f"Email sent successfully to {recipient_email}")
                    except Exception as e:
                        # Log error but continue with other recipients
                        error_msg = f"Error sending email to {recipient_email}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg, exc_info=True)
                
                response_data = {
                    'status': 'sent',
                    'message': f'Email sent successfully to {email_sent_count} recipient(s)',
                    'recipients_count': email_sent_count,
                    'sent_at': current_time.isoformat(),
                    'scheduled_at': None
                }
                
                if errors:
                    response_data['errors'] = errors
                    response_data['message'] = f'Email sent to {email_sent_count} recipient(s), but {len(errors)} failed'
                
                # Add warning if using console backend
                if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
                    response_data['warning'] = 'Email backend is set to console - emails are only printed to console, not actually sent. Please configure SMTP settings to send real emails.'
                
                return Response(response_data, status=status.HTTP_200_OK)
                
            except Exception as e:
                error_msg = f'Error sending email: {str(e)}'
                logger.error(error_msg, exc_info=True)
                return Response(
                    {'error': error_msg},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            # Schedule email for later
            from Scheduler.tasks import send_scheduled_email
            
            logger.info(f"Scheduling email for {scheduled_at} (UTC: {scheduled_at_utc}) with {len(recipients)} recipients")
            
            # Create scheduled email task
            try:
                # Ensure recipients is a list (it should be from serializer validation)
                recipients_list = recipients if isinstance(recipients, list) else list(recipients) if recipients else []
                
                # Schedule the email sending task
                # Note: Celery's apply_async expects the eta to be a UTC datetime object
                result = send_scheduled_email.apply_async(
                    args=[template.id, recipients_list, placeholder_values or {}],
                    eta=scheduled_at_utc  # Use UTC time for Celery
                )
                
                logger.info(f"Email scheduled successfully for {scheduled_at} (UTC: {scheduled_at_utc}) with task ID: {result.id}")
                
                return Response({
                    'status': 'scheduled',
                    'message': f'Email scheduled for {scheduled_at.strftime("%Y-%m-%d %H:%M:%S %Z")}',
                    'recipients_count': len(recipients_list),
                    'scheduled_at': scheduled_at.isoformat(),
                    'sent_at': None,
                    'task_id': result.id
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                error_msg = f'Error scheduling email: {str(e)}'
                logger.error(error_msg, exc_info=True)
                return Response(
                    {'error': error_msg},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
