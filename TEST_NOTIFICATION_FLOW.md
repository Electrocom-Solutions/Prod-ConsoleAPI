# Testing Notification Flow - Quick Guide

## Issue: Badge Counter Not Updating

When you create a notification from Django console/admin, the badge counter should update automatically. Here's how to test and verify the complete flow.

## Step 1: Verify Token is Registered

```bash
cd API
python manage.py shell
```

```python
from Notifications.models import DeviceToken
from django.contrib.auth.models import User

# Get the logged-in user from mobile app
user = User.objects.get(username='employee_username')  # Replace with actual username

# Check if token exists
tokens = DeviceToken.objects.filter(user=user, is_active=True)
print(f"Active tokens for {user.username}: {tokens.count()}")
for token in tokens:
    print(f"  - Token: {token.token[:50]}...")
    print(f"  - Device: {token.device_type}")
```

## Step 2: Create Notification from Django Admin

1. Go to Django Admin: `http://your-backend-url/admin/`
2. Navigate to: **Notifications** → **Notifications** → **Add Notification**
3. Fill in:
   - **Recipient**: Select the user who logged in from mobile app
   - **Title**: Test Notification
   - **Message**: This is a test
   - **Type**: System (or any type)
   - **Channel**: **In-App** (IMPORTANT: Must be "In-App" or "Push")
4. Click **Save**

**What should happen:**
- Notification is created
- FCM push is sent automatically
- Check Django logs for: "FCM push notification sent for notification X"

## Step 3: Create Notification from Django Console

```python
from Notifications.models import Notification
from django.contrib.auth.models import User
from django.utils import timezone
from Notifications.utils import send_fcm_push_notification

# Get the user
user = User.objects.get(username='employee_username')

# Create notification
notification = Notification.objects.create(
    recipient=user,
    title='Test from Console',
    message='This notification was created from Django console',
    type=Notification.Type.SYSTEM,
    channel=Notification.Channel.IN_APP,
    sent_at=timezone.now(),
    created_by=user  # or get admin user
)

# Send FCM push (this is now automatic in admin, but needed for console)
send_fcm_push_notification(
    user=user,
    title=notification.title,
    message=notification.message,
    notification_type=notification.type,
    notification_id=notification.id
)

print(f"Notification {notification.id} created and FCM sent")
```

## Step 4: Check Django Logs

After creating notification, check logs:

```bash
# Development
# Watch terminal where Django is running

# Production
tail -f /var/log/django/django.log | grep -i "fcm\|notification"
```

**Look for:**
```
INFO: FCM push notification sent for notification X to user employee_username
INFO: Sent push notification to 1 devices for user employee_username
```

**If you see errors:**
```
ERROR: Failed to send FCM push notification: ...
WARNING: No active device tokens found for user ...
```

## Step 5: Check Mobile App

### Expected Behavior:

1. **If app is in foreground:**
   - Local notification should appear
   - Badge counter should update to 1
   - Notification list should refresh automatically

2. **If app is in background:**
   - Push notification should appear in system tray
   - Badge counter should update
   - Tapping notification opens app

3. **If app is closed:**
   - Push notification appears in system tray
   - Tapping opens app and shows notification

### Check Mobile App Logs:

Look for:
```
📩 Foreground notification received: Test Notification
```

If you DON'T see this, the FCM message isn't reaching the app.

## Step 6: Troubleshooting

### Issue: No FCM Push Sent

**Check:**
1. Django logs for errors
2. Firebase Admin SDK initialization: Should see "Firebase Admin initialized"
3. Device token exists and is active
4. Channel is "In-App" or "Push" (not "Email")

**Fix:**
```python
# In Django shell, manually send FCM
from Notifications.utils import send_fcm_push_notification
from django.contrib.auth.models import User

user = User.objects.get(username='employee_username')
send_fcm_push_notification(
    user=user,
    title='Manual Test',
    message='Testing FCM',
    notification_type='System',
    notification_id=None
)
```

### Issue: FCM Sent but Not Received

**Check:**
1. Mobile app logs for FCM errors
2. Firebase Console → Cloud Messaging → Check delivery reports
3. Device token is still valid (not marked inactive)

**Verify token:**
```python
from Notifications.models import DeviceToken
token = DeviceToken.objects.filter(user=user, is_active=True).first()
print(f"Token active: {token.is_active}")
print(f"Token: {token.token[:50]}...")
```

### Issue: Badge Counter Not Updating

**Check:**
1. Notification provider is refreshing: Look for "📩 Foreground notification received" in logs
2. `fetchNotifications()` is being called after FCM message
3. Unread count is calculated correctly

**Manual refresh test:**
- Open notifications screen in mobile app
- Pull to refresh
- Badge should update

## Quick Test Script

```python
# Complete test script - run in Django shell
from Notifications.models import Notification, DeviceToken
from django.contrib.auth.models import User
from django.utils import timezone
from Notifications.utils import send_fcm_push_notification

# 1. Get user
username = 'employee_username'  # Replace with actual
user = User.objects.get(username=username)

# 2. Check token
tokens = DeviceToken.objects.filter(user=user, is_active=True)
print(f"✅ Active tokens: {tokens.count()}")
if tokens.count() == 0:
    print("❌ No active tokens! User needs to login from mobile app.")
    exit()

# 3. Create notification
notification = Notification.objects.create(
    recipient=user,
    title='Test Notification',
    message='Testing badge counter update',
    type=Notification.Type.SYSTEM,
    channel=Notification.Channel.IN_APP,
    sent_at=timezone.now(),
)

# 4. Send FCM
result = send_fcm_push_notification(
    user=user,
    title=notification.title,
    message=notification.message,
    notification_type=notification.type,
    notification_id=notification.id
)

print(f"✅ Notification {notification.id} created")
print(f"✅ FCM sent to {result} device(s)")
print("📱 Check mobile app - badge should update to 1")
```

## Expected Log Flow

**Backend (Django):**
```
INFO: FCM push notification sent for notification 123 to user employee_username
INFO: Sent push notification to 1 devices for user employee_username
```

**Mobile App (Flutter):**
```
📩 Foreground notification received: Test Notification
📩 Local notification shown: Test Notification
```

**Result:**
- Badge counter shows: **1**
- Notification appears in notifications list
- Notification is unread (red dot/badge)

---

**Last Updated**: 2025-01-27

