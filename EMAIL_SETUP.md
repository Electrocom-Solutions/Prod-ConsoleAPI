# Email Configuration Guide

## Current Issue
The email backend is currently set to `console`, which only prints emails to the console instead of actually sending them. To send real emails, you need to configure SMTP settings.

## Configuration Steps

### 1. Update `.env` file

Open `API/.env` and update the email configuration section:

#### For Gmail (Recommended for Development)
```env
# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
DEFAULT_FROM_EMAIL=your_email@gmail.com
```

#### For Other SMTP Servers
```env
# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.your-provider.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
# OR for SSL
# EMAIL_PORT=465
# EMAIL_USE_SSL=True
EMAIL_HOST_USER=your_email@yourdomain.com
EMAIL_HOST_PASSWORD=your_password
DEFAULT_FROM_EMAIL=your_email@yourdomain.com
```

### 2. Gmail App Password Setup

If using Gmail, you need to create an App Password:

1. Go to your Google Account settings: https://myaccount.google.com/
2. Navigate to **Security** → **2-Step Verification** (enable if not already enabled)
3. Scroll down to **App passwords**
4. Select **Mail** and **Other (Custom name)**
5. Enter a name like "Django Email"
6. Click **Generate**
7. Copy the 16-character password
8. Use this password in `EMAIL_HOST_PASSWORD` (not your regular Gmail password)

### 3. Restart Django Server

After updating the `.env` file, restart your Django server:

```bash
cd API
python manage.py runserver
```

### 4. Test Email Sending

1. Go to Email Templates dashboard
2. Click "Send Mail" on any template
3. Enter recipient email address
4. Click "Send"
5. Check if email is received

### 5. Check Logs

If emails still don't send, check the Django logs for error messages. Common issues:

- **Authentication failed**: Check `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD`
- **Connection refused**: Check `EMAIL_HOST` and `EMAIL_PORT`
- **TLS/SSL error**: Try switching between `EMAIL_USE_TLS` and `EMAIL_USE_SSL`

### 6. Production Email Services

For production, consider using:
- **SendGrid**: https://sendgrid.com/
- **Mailgun**: https://www.mailgun.com/
- **Amazon SES**: https://aws.amazon.com/ses/
- **Postmark**: https://postmarkapp.com/

These services provide better deliverability and tracking.

## Troubleshooting

### Console Backend (Current)
If `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend`, emails will only print to the console where Django is running. Check your terminal/console output to see the email content.

### SMTP Not Working
1. Verify SMTP credentials are correct
2. Check firewall/network settings
3. Ensure 2FA is enabled for Gmail (required for App Passwords)
4. Check spam/junk folder
5. Verify recipient email address is correct

### Error Messages
- Check Django server logs for detailed error messages
- The API response will include error details if email sending fails
- Check `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` are set correctly

