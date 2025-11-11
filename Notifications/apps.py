from django.apps import AppConfig
import logging
import os

logger = logging.getLogger(__name__)


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Notifications'
    
    def ready(self):
        """Initialize Firebase Admin SDK when Django starts"""
        try:
            import firebase_admin
            from firebase_admin import credentials
            
            # Check if already initialized
            try:
                firebase_admin.get_app()
                logger.info("Firebase Admin SDK already initialized")
                return
            except ValueError:
                # Not initialized, proceed with initialization
                pass
            
            # Try to get credentials from environment variable
            cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', None)
            if cred_path and os.path.exists(cred_path):
                try:
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                    logger.info(f"✅ Firebase Admin SDK initialized from {cred_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to initialize Firebase Admin SDK from {cred_path}: {str(e)}")
            else:
                # Try default credentials (for GCP environments)
                try:
                    firebase_admin.initialize_app()
                    logger.info("✅ Firebase Admin SDK initialized with default credentials")
                except Exception as e:
                    if cred_path:
                        logger.warning(f"⚠️ Firebase Admin SDK initialization failed. Credentials path: {cred_path}, Error: {str(e)}")
                    else:
                        logger.warning(f"⚠️ Firebase Admin SDK initialization failed. GOOGLE_APPLICATION_CREDENTIALS not set. Error: {str(e)}")
        except ImportError:
            logger.warning("⚠️ firebase-admin package not installed. FCM push notifications will not work.")
        except Exception as e:
            logger.error(f"❌ Unexpected error initializing Firebase Admin SDK: {str(e)}")
