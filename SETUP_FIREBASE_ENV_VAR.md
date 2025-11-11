# Setting Up Firebase Admin SDK Environment Variable for Gunicorn

## Problem

Firebase Admin SDK is not initialized because `GOOGLE_APPLICATION_CREDENTIALS` environment variable is not available to Gunicorn process.

## Solution: Set Environment Variable in Systemd Service

### Step 1: Edit Gunicorn Service File

```bash
sudo nano /etc/systemd/system/gunicorn-console-electrocom.service
```

### Step 2: Add Environment Variable

Add the `Environment` directive in the `[Service]` section:

```ini
[Unit]
Description=gunicorn daemon for console-electrocom
After=network.target

[Service]
User=vaibhav
Group=www-data
WorkingDirectory=/home/vaibhav/Prod-ConsoleAPI
Environment="GOOGLE_APPLICATION_CREDENTIALS=/home/vaibhav/Prod-ConsoleAPI/firebase-admin-sdk-key.json"
ExecStart=/home/vaibhav/Prod-ConsoleAPI/venv/bin/gunicorn \
    --access-logfile - \
    --workers 3 \
    --bind unix:/run/gunicorn-console-electrocom.sock \
    Integrations.wsgi:application

[Install]
WantedBy=multi-user.target
```

**Key line to add:**
```ini
Environment="GOOGLE_APPLICATION_CREDENTIALS=/home/vaibhav/Prod-ConsoleAPI/firebase-admin-sdk-key.json"
```

### Step 3: Reload Systemd and Restart Service

```bash
# Reload systemd to read new service file
sudo systemctl daemon-reload

# Restart Gunicorn service
sudo systemctl restart gunicorn-console-electrocom

# Check status
sudo systemctl status gunicorn-console-electrocom
```

### Step 4: Verify Environment Variable is Set

```bash
# Check if environment variable is set
sudo systemctl show gunicorn-console-electrocom | grep GOOGLE

# Should show:
# GOOGLE_APPLICATION_CREDENTIALS=/home/vaibhav/Prod-ConsoleAPI/firebase-admin-sdk-key.json
```

### Step 5: Check Django Logs for Initialization

```bash
# Check if Firebase Admin SDK initialized successfully
sudo journalctl -u gunicorn-console-electrocom -n 50 | grep -i "firebase\|fcm"

# Should see:
# ✅ Firebase Admin SDK initialized from /home/vaibhav/Prod-ConsoleAPI/firebase-admin-sdk-key.json
```

## Alternative: Multiple Environment Variables

If you need to set multiple environment variables:

```ini
[Service]
Environment="GOOGLE_APPLICATION_CREDENTIALS=/home/vaibhav/Prod-ConsoleAPI/firebase-admin-sdk-key.json"
Environment="DJANGO_SETTINGS_MODULE=Integrations.settings"
Environment="PYTHONPATH=/home/vaibhav/Prod-ConsoleAPI"
```

Or use `EnvironmentFile` to load from a file:

```ini
[Service]
EnvironmentFile=/home/vaibhav/Prod-ConsoleAPI/.env
```

**Note**: If using `EnvironmentFile`, make sure `.env` file has the format:
```
GOOGLE_APPLICATION_CREDENTIALS=/home/vaibhav/Prod-ConsoleAPI/firebase-admin-sdk-key.json
```

## Verify It's Working

After restarting, test by creating a notification:

1. Go to Django Admin
2. Create a notification with Channel = "In-App" or "Push"
3. Check logs:
   ```bash
   sudo journalctl -u gunicorn-console-electrocom -f | grep -i "fcm\|notification"
   ```
4. Should see:
   ```
   INFO: FCM push notification sent for notification X
   INFO: Sent push notification to 1 devices for user vaibhav
   ```

## Troubleshooting

### If environment variable still not set:

1. **Check service file syntax:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart gunicorn-console-electrocom
   ```

2. **Check file permissions:**
   ```bash
   ls -l /home/vaibhav/Prod-ConsoleAPI/firebase-admin-sdk-key.json
   # Should be readable by vaibhav user
   ```

3. **Test manually:**
   ```bash
   cd /home/vaibhav/Prod-ConsoleAPI
   source venv/bin/activate
   export GOOGLE_APPLICATION_CREDENTIALS=/home/vaibhav/Prod-ConsoleAPI/firebase-admin-sdk-key.json
   python manage.py shell
   ```
   Then in shell:
   ```python
   import firebase_admin
   firebase_admin.get_app()  # Should not raise ValueError
   ```

---

**Last Updated**: 2025-11-11

