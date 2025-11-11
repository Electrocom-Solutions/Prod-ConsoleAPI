# Troubleshooting: No FCM Tokens in Django Admin

If you don't see any tokens in the DeviceToken admin panel, follow these steps to diagnose and fix the issue.

## Quick Checklist

- [ ] User has logged in from the mobile app
- [ ] FCM token is generated (check mobile app logs)
- [ ] Token registration API call is successful (check Django logs)
- [ ] DeviceToken model is migrated
- [ ] User has proper permissions

---

## Step 1: Verify Mobile App is Registering Tokens

### Check Mobile App Logs

When a user logs in, you should see these logs in the Flutter console:

```
✅ User granted notification permission
📱 FCM Token: [LONG_TOKEN_STRING]
✅ FCM token registered successfully
```

**If you DON'T see these logs:**

1. **Check notification permissions**:
   - Android: Settings → Apps → Your App → Notifications
   - iOS: Settings → Your App → Notifications

2. **Check Firebase configuration**:
   - Verify `google-services.json` is in `MobileApp/android/app/`
   - Verify Firebase is initialized in `main.dart`

3. **Check FCM initialization**:
   - Look for errors like: `⚠️ FCM initialization error`
   - Check if `firebase_core` and `firebase_messaging` are properly installed

### Test Token Generation Manually

Add this to your Flutter app temporarily to test:

```dart
// In your login screen or after login
final fcmService = FCMService();
await fcmService.initialize();
final token = fcmService.fcmToken;
print('FCM Token: $token');
if (token != null) {
  await fcmService.registerToken();
}
```

---

## Step 2: Check Django Logs for Token Registration

### View Django Logs

**Development**:
```bash
cd API
python manage.py runserver
# Watch the terminal output
```

**Production**:
```bash
# Systemd
sudo journalctl -u your-django-service -f | grep -i "token\|fcm"

# Or log file
tail -f /var/log/django/django.log | grep -i "token\|fcm"
```

### What to Look For

**Success logs**:
```
INFO: Registering FCM token for user employee_username (device_type: android, device_id: ...)
INFO: FCM token created successfully for user employee_username (token_id: 1)
```

**Error logs**:
```
WARNING: Token registration failed: No token provided for user ...
ERROR: ...
```

### If No Logs Appear

This means the API endpoint is not being called. Check:

1. **API endpoint is accessible**:
   ```bash
   curl -X POST http://your-backend-url/api/notifications/register-token/ \
     -H "Content-Type: application/json" \
     -H "Cookie: sessionid=YOUR_SESSION" \
     -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
     -d '{"token": "test_token"}'
   ```

2. **Check API configuration**:
   - Verify `ApiConfig.notificationsListEndpoint` is correct
   - Check if the endpoint path is: `/api/notifications/register-token/`

3. **Check authentication**:
   - User must be logged in (session must be valid)
   - CSRF token must be included in request

---

## Step 3: Verify Database and Migrations

### Check if DeviceToken Table Exists

```bash
cd API
python manage.py shell
```

```python
from Notifications.models import DeviceToken
from django.contrib.auth.models import User

# Check if table exists
print(DeviceToken.objects.count())  # Should show 0 or number of tokens

# Check if any tokens exist (even if not showing in admin)
all_tokens = DeviceToken.objects.all()
for token in all_tokens:
    print(f"User: {token.user.username}, Token: {token.token[:50]}..., Active: {token.is_active}")
```

### Run Migrations

```bash
cd API
python manage.py makemigrations
python manage.py migrate
```

### Check Migration Status

```bash
python manage.py showmigrations Notifications
```

All migrations should show `[X]` (applied).

---

## Step 4: Test Token Registration Manually

### Using Django Shell

```bash
cd API
python manage.py shell
```

```python
from Notifications.models import DeviceToken
from django.contrib.auth.models import User

# Get a user
user = User.objects.get(username='employee_username')  # Replace with actual username

# Create a test token
test_token = DeviceToken.objects.create(
    user=user,
    token='test_fcm_token_12345',
    device_type='android',
    device_id='test_device_id',
    is_active=True
)

print(f"Created token: {test_token.id}")
print(f"User: {test_token.user.username}")
print(f"Token: {test_token.token}")
```

Then check Django Admin - you should see this test token.

### Using API (with Authentication)

```bash
# First, login to get session cookie
curl -X POST http://your-backend-url/api/auth/employee-mobile-login/ \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{
    "mobile_number": "YOUR_MOBILE",
    "password": "YOUR_PASSWORD"
  }'

# Extract CSRF token from cookies
CSRF_TOKEN=$(grep csrftoken cookies.txt | awk '{print $7}')

# Register token
curl -X POST http://your-backend-url/api/notifications/register-token/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -b cookies.txt \
  -d '{
    "token": "test_fcm_token_manual_123",
    "device_type": "android",
    "device_id": "test_device_123"
  }'
```

---

## Step 5: Check Admin Panel Configuration

### Verify Admin Registration

```bash
cd API
python manage.py shell
```

```python
from django.contrib import admin
from Notifications.models import DeviceToken

# Check if DeviceToken is registered
print(DeviceToken in admin.site._registry)
# Should print: True

# Check admin class
from Notifications.admin import DeviceTokenAdmin
print(DeviceTokenAdmin)
```

### Check Admin Permissions

1. Go to Django Admin: `http://your-backend-url/admin/`
2. Check if you're logged in as a superuser
3. Navigate to: **Notifications** → **Device tokens**
4. If you see "You don't have permission", you need superuser access

### Create Superuser (if needed)

```bash
cd API
python manage.py createsuperuser
```

---

## Step 6: Common Issues and Solutions

### Issue: Tokens Created but Not Visible in Admin

**Solution**: 
- Clear browser cache
- Refresh admin page
- Check if you're filtering by user (clear filters)

### Issue: "No tokens found" but logs show registration

**Possible causes**:
1. **Different user**: Token registered for different user than you're viewing
2. **Filter active**: Check if any filters are applied in admin
3. **Database connection**: Verify you're looking at the correct database

**Solution**:
```python
# In Django shell
from Notifications.models import DeviceToken
print(f"Total tokens: {DeviceToken.objects.count()}")
print(f"Active tokens: {DeviceToken.objects.filter(is_active=True).count()}")
```

### Issue: Token Registration Fails Silently

**Check**:
1. Django logs for errors
2. Mobile app logs for API errors
3. Network tab in browser/dev tools for failed requests

**Enable Debug Logging**:

Add to `settings.py`:
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'Notifications': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

### Issue: CSRF Token Error

**Symptoms**: 
- 403 Forbidden error
- "CSRF token missing or incorrect"

**Solution**:
1. Verify `ApiService` includes CSRF token in headers
2. Check if session is maintained after login
3. Verify `csrftoken` cookie is being sent

---

## Step 7: Verify End-to-End Flow

### Complete Test Flow

1. **Login from Mobile App**:
   - Open mobile app
   - Login with employee credentials
   - Watch Flutter console for FCM logs

2. **Check Django Logs**:
   - Should see: "Registering FCM token for user..."
   - Should see: "FCM token created successfully..."

3. **Check Database**:
   ```python
   from Notifications.models import DeviceToken
   DeviceToken.objects.all()
   ```

4. **Check Django Admin**:
   - Go to admin panel
   - Navigate to Device tokens
   - Should see the token

---

## Debugging Commands Summary

```bash
# Check Django logs
tail -f /var/log/django/django.log | grep -i token

# Check database
python manage.py shell
>>> from Notifications.models import DeviceToken
>>> DeviceToken.objects.count()

# Test API endpoint
curl -X POST http://your-backend-url/api/notifications/register-token/ \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=..." \
  -H "X-CSRFToken: ..." \
  -d '{"token": "test"}'

# Check migrations
python manage.py showmigrations Notifications

# Run migrations
python manage.py migrate
```

---

## Still Not Working?

If tokens still don't appear:

1. **Check all logs** (mobile app, Django, server)
2. **Verify database connection** (are you looking at the right database?)
3. **Test with manual token creation** (Django shell)
4. **Check for errors in browser console** (if testing via web)
5. **Verify user authentication** (is session valid?)

---

**Last Updated**: 2025-01-27

