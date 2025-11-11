"""
Utility functions for sending notifications.
"""
import logging
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Notification, DeviceToken

logger = logging.getLogger(__name__)


def send_fcm_push_notification(user, title, message, notification_type, notification_id=None):
    """
    Send FCM push notification to user's devices.
    
    Args:
        user: User instance
        title: Notification title
        message: Notification message
        notification_type: Notification type
        notification_id: Optional notification ID for deep linking
    
    Returns:
        Number of successful sends
    """
    try:
        import firebase_admin
        from firebase_admin import messaging, credentials
        import os
        
        # Initialize Firebase Admin if not already initialized
        try:
            firebase_admin.get_app()
        except ValueError:
            # Firebase not initialized, try to initialize it
            try:
                # Try to get credentials from environment variable
                cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', None)
                if cred_path and os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                    logger.info("Firebase Admin initialized from GOOGLE_APPLICATION_CREDENTIALS")
                else:
                    # Try to use default credentials (for GCP environments)
                    try:
                        firebase_admin.initialize_app()
                        logger.info("Firebase Admin initialized with default credentials")
                    except Exception as e:
                        logger.warning(f"Firebase Admin initialization failed: {str(e)}. Push notifications will be skipped.")
                        return 0
            except Exception as e:
                logger.warning(f"Firebase Admin not initialized. Skipping push notification: {str(e)}")
                return 0
        
        # Get active device tokens for the user
        device_tokens = DeviceToken.objects.filter(
            user=user,
            is_active=True
        ).values_list('token', flat=True)
        
        if not device_tokens:
            logger.info(f"No active device tokens found for user {user.username}")
            return 0
        
        # Prepare notification data
        notification_data = {
            'type': 'notification',
            'notification_id': str(notification_id) if notification_id else '',
            'notification_type': notification_type,
        }
        
        # Create message
        message_obj = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=message,
            ),
            data=notification_data,
            tokens=list(device_tokens),
        )
        
        # Send message
        response = messaging.send_multicast(message_obj)
        
        # Handle invalid tokens
        if response.failure_count > 0:
            invalid_tokens = []
            for idx, result in enumerate(response.responses):
                if not result.success:
                    invalid_tokens.append(list(device_tokens)[idx])
                    logger.warning(f"Failed to send to token: {result.exception}")
            
            # Mark invalid tokens as inactive
            if invalid_tokens:
                DeviceToken.objects.filter(token__in=invalid_tokens).update(is_active=False)
        
        logger.info(f"Sent push notification to {response.success_count} devices for user {user.username}")
        return response.success_count
        
    except ImportError:
        logger.warning("firebase-admin not installed. Skipping push notification.")
        return 0
    except Exception as e:
        logger.error(f"Error sending FCM push notification: {str(e)}")
        return 0


def send_notification(recipient, title, message, notification_type, channel=Notification.Channel.IN_APP, created_by=None):
    """
    Send a notification to a recipient.
    
    Args:
        recipient: User instance or list of User instances
        title: Notification title
        message: Notification message
        notification_type: Notification type (from Notification.Type)
        channel: Notification channel (default: IN_APP)
        created_by: User who created the notification (optional)
    
    Returns:
        Notification instance or list of Notification instances
    """
    if isinstance(recipient, list):
        notifications = []
        for user in recipient:
            notification = Notification.objects.create(
                recipient=user,
                title=title,
                message=message,
                type=notification_type,
                channel=channel,
                sent_at=timezone.now(),
                created_by=created_by
            )
            notifications.append(notification)
            
            # Send FCM push notification if channel includes Push
            if channel == Notification.Channel.PUSH or channel == Notification.Channel.IN_APP:
                send_fcm_push_notification(
                    user=user,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    notification_id=notification.id
                )
        return notifications
    else:
        notification = Notification.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            type=notification_type,
            channel=channel,
            sent_at=timezone.now(),
            created_by=created_by
        )
        
        # Send FCM push notification if channel includes Push
        if channel == Notification.Channel.PUSH or channel == Notification.Channel.IN_APP:
            send_fcm_push_notification(
                user=recipient,
                title=title,
                message=message,
                notification_type=notification_type,
                notification_id=notification.id
            )
        
        return notification


def send_notification_to_owners(title, message, notification_type, channel=Notification.Channel.IN_APP, created_by=None):
    """
    Send a notification to all superadmins (owners).
    
    Args:
        title: Notification title
        message: Notification message
        notification_type: Notification type (from Notification.Type)
        channel: Notification channel (default: IN_APP)
        created_by: User who created the notification (optional)
    
    Returns:
        List of Notification instances
    """
    owners = User.objects.filter(is_superuser=True)
    return send_notification(recipient=list(owners), title=title, message=message, 
                           notification_type=notification_type, channel=channel, created_by=created_by)


def send_notification_to_employees(title, message, notification_type, channel=Notification.Channel.IN_APP, created_by=None):
    """
    Send a notification to all employees.
    
    Args:
        title: Notification title
        message: Notification message
        notification_type: Notification type (from Notification.Type)
        channel: Notification channel (default: IN_APP)
        created_by: User who created the notification (optional)
    
    Returns:
        List of Notification instances
    """
    from HR.models import Employee
    
    employees = Employee.objects.select_related('profile', 'profile__user').filter(
        profile__user__isnull=False
    )
    
    employee_users = [emp.profile.user for emp in employees if emp.profile and emp.profile.user]
    
    return send_notification(recipient=employee_users, title=title, message=message,
                           notification_type=notification_type, channel=channel, created_by=created_by)


def send_notification_to_user(user, title, message, notification_type, channel=Notification.Channel.IN_APP, created_by=None):
    """
    Send a notification to a specific user.
    
    Args:
        user: User instance
        title: Notification title
        message: Notification message
        notification_type: Notification type (from Notification.Type)
        channel: Notification channel (default: IN_APP)
        created_by: User who created the notification (optional)
    
    Returns:
        Notification instance
    """
    return send_notification(recipient=user, title=title, message=message,
                           notification_type=notification_type, channel=channel, created_by=created_by)

