#!/usr/bin/env python
"""
Quick script to check notification and FCM status
Run: python manage.py shell < check_notification_status.py
Or: python check_notification_status.py (after setting up Django)
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Integrations.settings')
django.setup()

from Notifications.models import Notification, DeviceToken
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

print("=" * 60)
print("NOTIFICATION & FCM STATUS CHECK")
print("=" * 60)

# 1. Check recent notifications
print("\n1. RECENT NOTIFICATIONS (Last 5):")
print("-" * 60)
recent_notifications = Notification.objects.filter(
    sent_at__isnull=False
).order_by('-created_at')[:5]

if recent_notifications:
    for notif in recent_notifications:
        print(f"ID: {notif.id}")
        print(f"  Title: {notif.title}")
        print(f"  Recipient: {notif.recipient.username}")
        print(f"  Channel: {notif.channel}")
        print(f"  Sent At: {notif.sent_at}")
        print(f"  Created: {notif.created_at}")
        print()
else:
    print("  No sent notifications found")

# 2. Check device tokens
print("\n2. DEVICE TOKENS STATUS:")
print("-" * 60)
all_tokens = DeviceToken.objects.all()
active_tokens = DeviceToken.objects.filter(is_active=True)

print(f"Total tokens: {all_tokens.count()}")
print(f"Active tokens: {active_tokens.count()}")

if active_tokens.exists():
    print("\nActive tokens by user:")
    for token in active_tokens.select_related('user'):
        print(f"  User: {token.user.username}")
        print(f"    Device: {token.device_type}")
        print(f"    Token: {token.token[:50]}...")
        print(f"    Created: {token.created_at}")
        print()
else:
    print("  ⚠️  No active device tokens found!")
    print("  Users need to login from mobile app to register tokens")

# 3. Check notifications without tokens
print("\n3. NOTIFICATIONS WITHOUT ACTIVE TOKENS:")
print("-" * 60)
recent_notifs = Notification.objects.filter(
    sent_at__isnull=False,
    created_at__gte=timezone.now() - timedelta(hours=1)
).select_related('recipient')

notifications_without_tokens = []
for notif in recent_notifs:
    has_token = DeviceToken.objects.filter(
        user=notif.recipient,
        is_active=True
    ).exists()
    if not has_token:
        notifications_without_tokens.append(notif)

if notifications_without_tokens:
    print(f"Found {len(notifications_without_tokens)} recent notifications for users without active tokens:")
    for notif in notifications_without_tokens:
        print(f"  Notification {notif.id} → {notif.recipient.username} (no active token)")
else:
    print("  ✅ All recent notifications have active tokens")

# 4. Firebase Admin SDK check
print("\n4. FIREBASE ADMIN SDK STATUS:")
print("-" * 60)
try:
    import firebase_admin
    from firebase_admin import credentials
    import os
    
    try:
        app = firebase_admin.get_app()
        print("  ✅ Firebase Admin SDK is initialized")
    except ValueError:
        print("  ⚠️  Firebase Admin SDK not initialized")
        
        # Check credentials
        cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', None)
        if cred_path:
            if os.path.exists(cred_path):
                print(f"  ✅ Credentials file exists: {cred_path}")
                # Check permissions
                import stat
                file_stat = os.stat(cred_path)
                mode = stat.filemode(file_stat.st_mode)
                print(f"  📁 File permissions: {mode}")
            else:
                print(f"  ❌ Credentials file not found: {cred_path}")
        else:
            print("  ⚠️  GOOGLE_APPLICATION_CREDENTIALS not set")
            
except ImportError:
    print("  ❌ firebase-admin not installed")
    print("  Run: pip install firebase-admin")

# 5. Summary
print("\n5. SUMMARY:")
print("-" * 60)
if active_tokens.exists():
    print("  ✅ Device tokens are registered")
else:
    print("  ❌ No device tokens - users need to login from mobile app")

if recent_notifications.exists():
    latest = recent_notifications.first()
    has_token = DeviceToken.objects.filter(
        user=latest.recipient,
        is_active=True
    ).exists()
    if has_token:
        print(f"  ✅ Latest notification ({latest.id}) has active token for recipient")
    else:
        print(f"  ⚠️  Latest notification ({latest.id}) recipient has no active token")
        print(f"      Recipient: {latest.recipient.username}")

print("\n" + "=" * 60)
print("Next steps:")
print("1. Check Django logs for FCM sending: journalctl -u gunicorn -n 100 | grep FCM")
print("2. Check mobile app logs for received notifications")
print("3. Verify notification channel is 'In-App' or 'Push'")
print("=" * 60)

