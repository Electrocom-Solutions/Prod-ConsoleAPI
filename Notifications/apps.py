from django.apps import AppConfig
import logging
import os

logger = logging.getLogger(__name__)


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Notifications'
    
    def ready(self):
        """Initialize Firebase Admin SDK when Django starts"""
        # Use both print and logger for visibility
        print("🔧 Notifications app ready() called - initializing Firebase Admin SDK...")
        logger.info("Notifications app ready() called - initializing Firebase Admin SDK...")
        
        try:
            import firebase_admin
            from firebase_admin import credentials
            
            # Check if already initialized
            try:
                firebase_admin.get_app()
                msg = "Firebase Admin SDK already initialized"
                print(f"✅ {msg}")
                logger.info(msg)
                return
            except ValueError:
                # Not initialized, proceed with initialization
                pass
            
            # Try to get credentials from environment variable
            cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', None)
            print(f"🔍 Checking credentials: GOOGLE_APPLICATION_CREDENTIALS = {cred_path}")
            
            if cred_path and os.path.exists(cred_path):
                try:
                    print(f"📁 Credentials file exists: {cred_path}")
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                    msg = f"✅ Firebase Admin SDK initialized from {cred_path}"
                    print(msg)
                    logger.info(msg)
                except Exception as e:
                    msg = f"⚠️ Failed to initialize Firebase Admin SDK from {cred_path}: {str(e)}"
                    print(msg)
                    logger.warning(msg)
            else:
                # Try default credentials (for GCP environments)
                try:
                    print("🔍 Trying default credentials...")
                    firebase_admin.initialize_app()
                    msg = "✅ Firebase Admin SDK initialized with default credentials"
                    print(msg)
                    logger.info(msg)
                except Exception as e:
                    if cred_path:
                        msg = f"⚠️ Firebase Admin SDK initialization failed. Credentials path: {cred_path}, Error: {str(e)}"
                    else:
                        msg = f"⚠️ Firebase Admin SDK initialization failed. GOOGLE_APPLICATION_CREDENTIALS not set. Error: {str(e)}"
                    print(msg)
                    logger.warning(msg)
        except ImportError:
            msg = "⚠️ firebase-admin package not installed. FCM push notifications will not work."
            print(msg)
            logger.warning(msg)
        except Exception as e:
            msg = f"❌ Unexpected error initializing Firebase Admin SDK: {str(e)}"
            print(msg)
            logger.error(msg)
