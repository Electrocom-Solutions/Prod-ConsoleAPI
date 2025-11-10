# Celery Setup Guide for Scheduled Notifications and Emails

This guide explains how to set up Celery to handle scheduled notifications and emails.

## Overview

The application uses Celery with Redis as the message broker to schedule and execute tasks for:
- **Scheduled Notifications**: Notifications that are scheduled to be sent at a specific date/time
- **Scheduled Emails**: Emails that are scheduled to be sent at a specific date/time

## Prerequisites

1. **Redis** must be installed and running
2. **Celery** and **django-celery-beat** must be installed
3. **Celery Worker** must be running to process tasks
4. **Celery Beat** must be running to schedule periodic tasks (for fallback scheduled notification checking)

## Installation

### 1. Install Redis

**On macOS (using Homebrew):**
```bash
brew install redis
brew services start redis
```

**On Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

**On Windows:**
Download and install Redis from: https://redis.io/download

### 2. Verify Redis is Running

```bash
redis-cli ping
# Should return: PONG
```

### 3. Install Python Dependencies

The required packages should already be in `requirements.txt`:
- `celery`
- `redis`
- `django-celery-beat`

Install them:
```bash
cd API
pip install -r requirements.txt
```

## Configuration

### 1. Redis Configuration

Ensure Redis is running on the default port (6379) or update `CELERY_BROKER_URL` in `API/.env`:

```env
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=django-db
```

### 2. Celery Settings

The Celery configuration is in `API/API/settings.py`:

```python
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'django-db')
CELERY_TIMEZONE = 'Asia/Kolkata'
CELERY_ENABLE_UTC = True
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
```

## Running Celery

### 1. Start Celery Worker

The Celery worker processes tasks from the queue. **This must be running for scheduled tasks to execute.**

```bash
cd API
celery -A API worker -l info
```

**For production, run in the background:**
```bash
celery -A API worker -l info --detach
```

### 2. Start Celery Beat

Celery Beat is used for periodic tasks (like checking for scheduled notifications). **This should also be running.**

```bash
cd API
celery -A API beat -l info
```

**For production, run in the background:**
```bash
celery -A API beat -l info --detach
```

### 3. Run Both Together (Development)

You can run both worker and beat in the same process for development:

```bash
cd API
celery -A API worker --beat -l info
```

## How Scheduled Tasks Work

### Scheduled Notifications

1. **When a notification is scheduled:**
   - The system creates a Celery task scheduled for the specific date/time
   - The task is scheduled using `apply_async(eta=scheduled_at_utc)`
   - The datetime is converted to UTC for Celery (Celery uses UTC internally)
   - No notification records are created immediately

2. **When the scheduled time arrives:**
   - Celery executes the `send_scheduled_notification` task
   - The task creates notification records for all employees
   - Notifications appear in the notification list

3. **Notification List:**
   - Only shows notifications that have been sent (`sent_at` is not null)
   - Scheduled notifications (not yet sent) won't appear until they're actually sent

### Scheduled Emails

1. **When an email is scheduled:**
   - The system creates a Celery task scheduled for the specific date/time
   - The task is scheduled using `apply_async(eta=scheduled_at_utc)`
   - The datetime is converted to UTC for Celery

2. **When the scheduled time arrives:**
   - Celery executes the `send_scheduled_email` task
   - The task sends emails to all recipients
   - Emails are sent using Django's email backend

## Timezone Handling

- **Frontend**: Sends datetime in local timezone (Asia/Kolkata)
- **Backend**: Converts to UTC for Celery scheduling
- **Celery**: Uses UTC internally
- **Task Execution**: Executes at the correct time in UTC

## Troubleshooting

### Tasks Not Executing

1. **Check if Celery Worker is running:**
   ```bash
   ps aux | grep celery
   ```

2. **Check Redis connection:**
   ```bash
   redis-cli ping
   ```

3. **Check Celery logs:**
   - Look for error messages in the Celery worker output
   - Check Django logs for task execution errors

### Scheduled Tasks Not Appearing

1. **Check if tasks are being scheduled:**
   - Look for log messages: `"Notification scheduled successfully for..."`
   - Check Celery task results in Django admin (if using `django-db` backend)

2. **Verify timezone conversion:**
   - Check logs for: `"Scheduled time in UTC: ..."`
   - Ensure the scheduled time is in the future

### Notifications/Emails Not Being Sent

1. **Check Celery Worker logs:**
   - Look for task execution logs
   - Check for error messages

2. **Check Django logs:**
   - Look for notification/email creation logs
   - Check for SMTP configuration errors (for emails)

3. **Verify task registration:**
   - Ensure tasks are registered: `celery -A API inspect registered`

## Production Deployment

### Using systemd (Linux)

Create systemd service files for Celery worker and beat:

**`/etc/systemd/system/celery-worker.service`:**
```ini
[Unit]
Description=Celery Worker
After=network.target

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/path/to/API
ExecStart=/path/to/venv/bin/celery -A API worker -l info --detach
ExecStop=/bin/kill -s TERM $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/celery-beat.service`:**
```ini
[Unit]
Description=Celery Beat
After=network.target

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/path/to/API
ExecStart=/path/to/venv/bin/celery -A API beat -l info --detach
ExecStop=/bin/kill -s TERM $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start services:
```bash
sudo systemctl enable celery-worker
sudo systemctl enable celery-beat
sudo systemctl start celery-worker
sudo systemctl start celery-beat
```

### Using Supervisor

Create supervisor configuration files for Celery worker and beat:

**`/etc/supervisor/conf.d/celery-worker.conf`:**
```ini
[program:celery-worker]
command=/path/to/venv/bin/celery -A API worker -l info
directory=/path/to/API
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/worker.log
```

**`/etc/supervisor/conf.d/celery-beat.conf`:**
```ini
[program:celery-beat]
command=/path/to/venv/bin/celery -A API beat -l info
directory=/path/to/API
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/beat.log
```

Reload supervisor:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start celery-worker
sudo supervisorctl start celery-beat
```

## Monitoring

### Check Celery Worker Status

```bash
celery -A API inspect active
celery -A API inspect scheduled
celery -A API inspect registered
```

### Check Task Results

If using `django-db` backend, task results are stored in the database and can be viewed in Django admin.

### View Logs

- **Celery Worker logs**: Check the output of the celery worker process
- **Django logs**: Check Django application logs for task execution details
- **Redis logs**: Check Redis logs for broker connection issues

## Important Notes

1. **Celery Worker must be running**: Scheduled tasks will not execute if the Celery worker is not running
2. **Timezone handling**: Always ensure datetimes are converted to UTC for Celery
3. **Redis must be running**: Celery requires Redis (or another message broker) to be running
4. **Task registration**: Ensure all tasks are properly registered and discoverable by Celery
5. **Error handling**: Check logs regularly for task execution errors

## Testing

### Test Scheduled Notification

1. Schedule a notification for a few minutes in the future
2. Check Celery worker logs for task scheduling
3. Wait for the scheduled time
4. Check if notifications appear in the notification list
5. Verify notifications are created for all employees

### Test Scheduled Email

1. Schedule an email for a few minutes in the future
2. Check Celery worker logs for task scheduling
3. Wait for the scheduled time
4. Check if emails are sent (check SMTP logs or email inbox)
5. Verify emails are sent to all recipients

## Support

For issues or questions:
1. Check Celery worker logs
2. Check Django application logs
3. Verify Redis is running
4. Verify Celery worker and beat are running
5. Check timezone settings
6. Verify task registration

