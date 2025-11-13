"""
Authentication Views
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import login, logout
from django.utils import timezone
from datetime import timedelta
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.core.mail import send_mail
from django.conf import settings
import random
import logging

logger = logging.getLogger(__name__)

from .serializers import (
    OwnerLoginSerializer, 
    EmployeeMobileLoginSerializer,
    EmployeeForgotPasswordSerializer,
    EmployeeVerifyOTPSerializer,
    EmployeeResetPasswordSerializer
)


@swagger_auto_schema(
    method='post',
    operation_id='owner_login',
    operation_summary="Owner Login",
    operation_description="""
    Login endpoint for staff members and superusers to access the web application.
    
    **Requirements:**
    - User must be a staff member (is_staff=True) or superuser (is_superuser=True)
    - User account must be active
    - Only staff and superusers can access the web application
    
    **Features:**
    - Supports login with email, username, or mobile number
    - Remember me checkbox to extend session expiry
    - Returns user information and session details
    
    **Login Identifier Options:**
    - Email address (e.g., "owner@example.com")
    - Username (e.g., "admin")
    - Mobile number (e.g., "9876543210")
    
    **Remember Me:**
    - If checked: Session expires after 30 days
    - If unchecked: Session expires when browser closes (default)
    
    **Response:**
    Returns user details including username, email, first name, last name, is_staff, is_superuser, and login status.
    """,
    tags=['Authentication'],
    request_body=OwnerLoginSerializer,
    responses={
        200: openapi.Response(
            description="Login successful",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Login success status'),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message'),
                    'user': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='User ID'),
                            'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username'),
                            'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email address'),
                            'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='First name'),
                            'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Last name'),
                            'is_superuser': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is superuser'),
                            'is_staff': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is staff'),
                        }
                    ),
                    'session_expiry': openapi.Schema(type=openapi.TYPE_STRING, description='Session expiry date/time'),
                }
            )
        ),
        400: openapi.Response(
            description="Invalid credentials or validation error",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING, description='Error message')
                }
            )
        )
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def owner_login(request):
    """
    Owner login endpoint
    Supports login with email, username, or mobile number
    """
    serializer = OwnerLoginSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    user = serializer.validated_data['user']
    remember_me = serializer.validated_data.get('remember_me', False)
    
    # Log in the user
    login(request, user)
    
    # Set session expiry based on remember me
    if remember_me:
        # 30 days for remember me
        request.session.set_expiry(60 * 60 * 24 * 30)
        session_expiry = timezone.now() + timedelta(days=30)
    else:
        # Session expires when browser closes
        request.session.set_expiry(0)
        session_expiry = None
    
    return Response({
        'success': True,
        'message': 'Login successful',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
        },
        'session_expiry': session_expiry.isoformat() if session_expiry else None,
    }, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    operation_id='employee_mobile_login',
    operation_summary="Employee Mobile App Login",
    operation_description="""
    Login endpoint for employees to access the mobile application.
    
    **Features:**
    - Login with mobile number and password only
    - Returns employee information along with user details
    - Optimized for mobile app authentication
    - Session expires after 7 days
    
    **Request Fields:**
    - mobile_number: Employee's mobile number (e.g., "9876543210")
    - password: User password
    
    **Response:**
    Returns user details and employee information including employee code, designation, and profile information.
    """,
    tags=['Authentication'],
    request_body=EmployeeMobileLoginSerializer,
    responses={
        200: openapi.Response(
            description="Login successful",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Login success status'),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message'),
                    'user': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='User ID'),
                            'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username'),
                            'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email address'),
                            'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='First name'),
                            'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Last name'),
                        }
                    ),
                    'employee': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Employee ID'),
                            'employee_code': openapi.Schema(type=openapi.TYPE_STRING, description='Employee code'),
                            'designation': openapi.Schema(type=openapi.TYPE_STRING, description='Employee designation'),
                        }
                    ),
                }
            )
        ),
        400: openapi.Response(
            description="Invalid credentials or validation error",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING, description='Error message')
                }
            )
        )
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def employee_mobile_login(request):
    """
    Employee mobile app login endpoint
    Supports login with email, username, or mobile number
    """
    serializer = EmployeeMobileLoginSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    user = serializer.validated_data['user']
    employee = serializer.validated_data['employee']
    
    # Log in the user
    login(request, user)
    
    # For mobile app, set a reasonable session expiry (e.g., 7 days)
    request.session.set_expiry(60 * 60 * 24 * 7)
    
    return Response({
        'success': True,
        'message': 'Login successful',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        },
        'employee': {
            'id': employee.id,
            'employee_code': employee.employee_code,
            'designation': employee.designation,
        },
    }, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    operation_id='logout',
    operation_summary="Logout",
    operation_description="""
    Logout endpoint to end the current user session.
    
    **Features:**
    - Logs out the current authenticated user
    - Clears the session
    - Returns success message
    """,
    tags=['Authentication'],
    responses={
        200: openapi.Response(
            description="Logout successful",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Logout success status'),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message'),
                }
            )
        ),
        401: openapi.Response(
            description="Unauthorized",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING, description='Error message')
                }
            )
        )
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Logout endpoint
    """
    logout(request)
    return Response({
        'success': True,
        'message': 'Logout successful',
    }, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    operation_id='get_current_user',
    operation_summary="Get Current User",
    operation_description="""
    Get the current authenticated user's information.
    
    **Features:**
    - Returns user details for the currently authenticated user
    - Requires authentication
    """,
    tags=['Authentication'],
    responses={
        200: openapi.Response(
            description="User information",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'user': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='User ID'),
                            'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username'),
                            'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email address'),
                            'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='First name'),
                            'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Last name'),
                            'is_superuser': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is superuser'),
                            'is_staff': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is staff'),
                        }
                    ),
                }
            )
        ),
        401: openapi.Response(
            description="Unauthorized",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING, description='Error message')
                }
            )
        ),
        403: openapi.Response(
            description="Forbidden - User is not staff or superuser",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING, description='Error message')
                }
            )
        )
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """
    Get current user endpoint
    Requires authentication and staff/superuser status
    """
    user = request.user
    
    # Verify user is staff or superuser
    if not (user.is_staff or user.is_superuser):
        return Response({
            'error': 'Access denied. Only staff members and superusers can access the web application.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    return Response({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
        },
    }, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    operation_id='employee_forgot_password',
    operation_summary="Employee Forgot Password",
    operation_description="""
    Request password reset for employee mobile app.
    
    **Features:**
    - Accepts mobile number
    - Validates mobile number belongs to an employee
    - Generates 6-digit OTP
    - Sends OTP to employee's email address
    - Stores OTP in database for verification
    
    **Security:**
    - Does not reveal if mobile number exists (returns success message regardless)
    - OTP expires after 10 minutes
    - Rate limiting: Max 3 requests per mobile number per hour
    
    **Request Fields:**
    - mobile_number: Employee's mobile number (e.g., "9876543210")
    
    **Response:**
    Returns success message if mobile number is valid (for security, always returns success).
    """,
    tags=['Authentication'],
    request_body=EmployeeForgotPasswordSerializer,
    responses={
        200: openapi.Response(
            description="OTP sent successfully (or generic success message)",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Success status'),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message'),
                }
            )
        ),
        400: openapi.Response(
            description="Validation error",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING, description='Error message')
                }
            )
        )
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def employee_forgot_password(request):
    """
    Employee forgot password endpoint
    Sends OTP to employee's email for password reset
    """
    serializer = EmployeeForgotPasswordSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if user and employee exist (from serializer validation)
    user = serializer.validated_data.get('user')
    employee = serializer.validated_data.get('employee')
    
    # For security, always return success message
    # Only send OTP if user and employee exist
    if user and employee:
        # Rate limiting: Check if too many requests in last hour
        from Profiles.models import OTP
        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent_otps = OTP.objects.filter(
            user=user,
            otp_type=OTP.OTPType.E,
            otp_for=OTP.OTPFor.RESET,
            created_at__gte=one_hour_ago
        ).count()
        
        if recent_otps >= 3:
            # Still return success for security, but don't send OTP
            logger.warning(f"Rate limit exceeded for mobile number password reset: {serializer.validated_data.get('mobile_number')}")
            return Response({
                'success': True,
                'message': 'If the mobile number is registered, an OTP has been sent to your email address.'
            }, status=status.HTTP_200_OK)
        
        # Generate 6-digit OTP
        otp_code = str(random.randint(100000, 999999))
        
        # Get user's email
        user_email = user.email
        if not user_email:
            # If no email, return success anyway for security
            logger.warning(f"⚠️ User {user.id} ({user.username}) has no email address for password reset")
            logger.warning(f"⚠️ User profile email: {getattr(user, 'email', 'N/A')}")
            # Still return success for security
            return Response({
                'success': True,
                'message': 'If the mobile number is registered, an OTP has been sent to your email address.'
            }, status=status.HTTP_200_OK)
        
        logger.info(f"📧 User {user.id} email address: {user_email}")
        
        # Create OTP record
        otp_record = OTP.objects.create(
            user=user,
            otp=otp_code,
            otp_type=OTP.OTPType.E,
            otp_for=OTP.OTPFor.RESET,
            is_verified=False
        )
        
        # Send OTP email
        try:
            # Check if email backend is configured
            if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
                logger.warning("⚠️ EMAIL_BACKEND is set to console - OTP email will only be printed to console, not actually sent!")
                logger.warning(f"⚠️ OTP for user {user.id} ({user_email}): {otp_code}")
            
            # Check if email settings are configured
            from_email = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
            if not from_email:
                logger.error("❌ Email configuration is missing. DEFAULT_FROM_EMAIL and EMAIL_HOST_USER are not set.")
                # Still return success for security
            elif not settings.EMAIL_HOST:
                logger.error("❌ EMAIL_HOST is not configured in settings.")
                # Still return success for security
            else:
                subject = 'Password Reset OTP - Electrocom'
                message = f"""
Hello {user.first_name or 'Employee'},

You have requested to reset your password for your Electrocom employee account.

Your OTP code is: {otp_code}

This OTP will expire in 10 minutes.

If you did not request this password reset, please ignore this email.

Best regards,
Electrocom Team
"""
                html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #0ea5e9; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .otp-box {{ background-color: #fff; border: 2px solid #0ea5e9; padding: 15px; text-align: center; margin: 20px 0; }}
        .otp-code {{ font-size: 32px; font-weight: bold; color: #0ea5e9; letter-spacing: 5px; }}
        .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Password Reset Request</h1>
        </div>
        <div class="content">
            <p>Hello {user.first_name or 'Employee'},</p>
            <p>You have requested to reset your password for your Electrocom employee account.</p>
            <div class="otp-box">
                <p style="margin: 0 0 10px 0;">Your OTP code is:</p>
                <div class="otp-code">{otp_code}</div>
            </div>
            <p>This OTP will expire in <strong>10 minutes</strong>.</p>
            <p>If you did not request this password reset, please ignore this email.</p>
        </div>
        <div class="footer">
            <p>Best regards,<br>Electrocom Team</p>
        </div>
    </div>
</body>
</html>
"""
                
                logger.info(f"📧 Attempting to send OTP email to {user_email} for user {user.id}")
                logger.info(f"📧 Email config - Backend: {settings.EMAIL_BACKEND}, Host: {settings.EMAIL_HOST}, From: {from_email}")
                
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=from_email,
                    recipient_list=[user_email],
                    html_message=html_message,
                    fail_silently=False,
                )
                
                logger.info(f"✅ Password reset OTP sent successfully to {user_email} for user {user.id}")
        except Exception as e:
            logger.error(f"❌ Error sending password reset OTP email to {user_email}: {str(e)}", exc_info=True)
            logger.error(f"❌ Email config - Backend: {settings.EMAIL_BACKEND}, Host: {settings.EMAIL_HOST}, From: {from_email if 'from_email' in locals() else 'N/A'}")
            # Still return success for security
    
    return Response({
        'success': True,
        'message': 'If the mobile number is registered, an OTP has been sent to your email address.'
    }, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    operation_id='employee_verify_otp',
    operation_summary="Verify OTP for Password Reset",
    operation_description="""
    Verify OTP code for password reset.
    
    **Features:**
    - Validates OTP code
    - Checks if OTP is not expired (10 minutes)
    - Marks OTP as verified
    
    **Request Fields:**
    - mobile_number: Employee's mobile number
    - otp: 6-digit OTP code
    
    **Response:**
    Returns success message if OTP is valid.
    """,
    tags=['Authentication'],
    request_body=EmployeeVerifyOTPSerializer,
    responses={
        200: openapi.Response(
            description="OTP verified successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Success status'),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message'),
                }
            )
        ),
        400: openapi.Response(
            description="Invalid or expired OTP",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING, description='Error message')
                }
            )
        )
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def employee_verify_otp(request):
    """
    Employee verify OTP endpoint
    Verifies OTP code for password reset
    """
    serializer = EmployeeVerifyOTPSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    otp_record = serializer.validated_data['otp_record']
    
    # Mark OTP as verified
    otp_record.is_verified = True
    otp_record.save()
    
    return Response({
        'success': True,
        'message': 'OTP verified successfully. You can now reset your password.'
    }, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    operation_id='employee_reset_password',
    operation_summary="Reset Employee Password",
    operation_description="""
    Reset employee password using verified OTP.
    
    **Features:**
    - Validates OTP is verified
    - Validates passwords match
    - Updates user password
    - Invalidates used OTP
    
    **Request Fields:**
    - mobile_number: Employee's mobile number
    - otp: 6-digit OTP code (must be verified)
    - new_password: New password (minimum 6 characters)
    - confirm_password: Confirm new password
    
    **Response:**
    Returns success message if password is reset successfully.
    """,
    tags=['Authentication'],
    request_body=EmployeeResetPasswordSerializer,
    responses={
        200: openapi.Response(
            description="Password reset successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Success status'),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message'),
                }
            )
        ),
        400: openapi.Response(
            description="Validation error",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING, description='Error message')
                }
            )
        )
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def employee_reset_password(request):
    """
    Employee reset password endpoint
    Resets password using verified OTP
    """
    serializer = EmployeeResetPasswordSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    user = serializer.validated_data['user']
    new_password = serializer.validated_data['new_password']
    otp_record = serializer.validated_data['otp_record']
    
    # Update password
    user.set_password(new_password)
    user.save()
    
    # Delete the used OTP record and all other password reset OTPs for this user
    # to prevent reuse and clean up old OTPs
    from Profiles.models import OTP
    OTP.objects.filter(
        user=user,
        otp_type=OTP.OTPType.E,
        otp_for=OTP.OTPFor.RESET
    ).delete()
    
    logger.info(f"Password reset successful for user {user.id}. All password reset OTPs deleted.")
    
    return Response({
        'success': True,
        'message': 'Password has been reset successfully. You can now login with your new password.'
    }, status=status.HTTP_200_OK)
