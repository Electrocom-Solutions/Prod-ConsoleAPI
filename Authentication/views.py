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

from .serializers import OwnerLoginSerializer, EmployeeMobileLoginSerializer


@swagger_auto_schema(
    method='post',
    operation_id='owner_login',
    operation_summary="Owner Login",
    operation_description="""
    Login endpoint for owners (superusers/admins) to access the system.
    
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
    Returns user details including username, email, first name, last name, and login status.
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
        )
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """
    Get current user endpoint
    """
    user = request.user
    return Response({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_superuser': user.is_superuser,
        },
    }, status=status.HTTP_200_OK)
