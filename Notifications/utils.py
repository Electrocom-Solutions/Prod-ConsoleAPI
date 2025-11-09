"""
Utility functions for sending notifications.
"""
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Notification


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
        return notifications
    else:
        return Notification.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            type=notification_type,
            channel=channel,
            sent_at=timezone.now(),
            created_by=created_by
        )


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

