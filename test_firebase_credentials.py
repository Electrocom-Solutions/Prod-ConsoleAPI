#!/usr/bin/env python
"""
Test Firebase Admin SDK credentials and FCM configuration
Run: python manage.py shell < test_firebase_credentials.py
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Integrations.settings')
django.setup()

import json
from firebase_admin import credentials, messaging
import firebase_admin

print("=" * 60)
print("FIREBASE CREDENTIALS VALIDATION")
print("=" * 60)

# 1. Check credentials file
cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', None)
print(f"\n1. Credentials Path: {cred_path}")

if not cred_path:
    print("   ❌ GOOGLE_APPLICATION_CREDENTIALS not set!")
    sys.exit(1)

if not os.path.exists(cred_path):
    print(f"   ❌ Credentials file not found: {cred_path}")
    sys.exit(1)

print(f"   ✅ Credentials file exists")

# 2. Read and validate credentials JSON
try:
    with open(cred_path, 'r') as f:
        cred_data = json.load(f)
    
    print(f"\n2. Credentials File Content:")
    print(f"   Project ID: {cred_data.get('project_id', 'NOT FOUND')}")
    print(f"   Client Email: {cred_data.get('client_email', 'NOT FOUND')}")
    print(f"   Type: {cred_data.get('type', 'NOT FOUND')}")
    
    if cred_data.get('type') != 'service_account':
        print("   ⚠️  Warning: Credentials type is not 'service_account'")
    
except Exception as e:
    print(f"   ❌ Error reading credentials file: {e}")
    sys.exit(1)

# 3. Initialize Firebase Admin SDK
print(f"\n3. Initializing Firebase Admin SDK...")
try:
    # Check if already initialized
    try:
        app = firebase_admin.get_app()
        print("   ✅ Firebase Admin SDK already initialized")
        print(f"   Project ID: {app.project_id}")
    except ValueError:
        # Not initialized, initialize it
        cred = credentials.Certificate(cred_path)
        app = firebase_admin.initialize_app(cred)
        print("   ✅ Firebase Admin SDK initialized successfully")
        print(f"   Project ID: {app.project_id}")
        
        # Verify project ID matches
        if app.project_id != cred_data.get('project_id'):
            print(f"   ⚠️  Warning: App project_id ({app.project_id}) doesn't match credentials project_id ({cred_data.get('project_id')})")
        
except Exception as e:
    print(f"   ❌ Error initializing Firebase Admin SDK: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. Test FCM API access
print(f"\n4. Testing FCM API Access...")
try:
    # Try to create a test message (we won't send it, just validate the API)
    test_message = messaging.Message(
        notification=messaging.Notification(
            title='Test',
            body='Test message'
        ),
        token='test_token_that_will_fail_but_validate_api'
    )
    
    # This will fail with invalid token, but if we get a different error (like 404),
    # it means the API endpoint is wrong
    try:
        messaging.send(test_message)
    except messaging.UnregisteredError:
        print("   ✅ FCM API is accessible (got expected invalid token error)")
    except Exception as e:
        error_str = str(e)
        if '404' in error_str or 'not found' in error_str.lower():
            print(f"   ❌ FCM API returned 404 - Project might not have FCM enabled")
            print(f"   Error: {e}")
        else:
            print(f"   ⚠️  Unexpected error (but API is accessible): {e}")
            
except Exception as e:
    error_str = str(e)
    if '404' in error_str:
        print(f"   ❌ FCM API returned 404")
        print(f"   This usually means:")
        print(f"   1. Firebase Cloud Messaging API is not enabled for this project")
        print(f"   2. Project ID in credentials doesn't match Firebase project")
        print(f"   3. Wrong credentials file for this project")
    else:
        print(f"   ❌ Error testing FCM API: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("RECOMMENDATIONS:")
print("=" * 60)
print("1. Verify Firebase project ID matches in Firebase Console")
print("2. Enable 'Firebase Cloud Messaging API (V1)' in Google Cloud Console")
print("3. Ensure credentials file is for the correct Firebase project")
print("4. Check Google Cloud Console -> APIs & Services -> Enabled APIs")
print("=" * 60)

