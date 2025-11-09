"""
Profile Views
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Profile
from .serializers import CurrentUserProfileSerializer, CurrentUserProfileUpdateSerializer


@swagger_auto_schema(
    method='get',
    operation_id='get_current_user_profile',
    operation_summary="Get Current User Profile",
    operation_description="""
    Get the current authenticated user's profile information.
    
    **Features:**
    - Returns user and profile details for the currently authenticated user
    - Includes photo URLs, document URLs, and phone number
    - Requires authentication
    """,
    tags=['Profile'],
    responses={
        200: openapi.Response(
            description="User profile information",
            schema=CurrentUserProfileSerializer()
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
        404: openapi.Response(
            description="Profile not found",
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
def get_current_user_profile(request):
    """
    Get current user profile endpoint
    """
    user = request.user
    
    try:
        profile = Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        # Create profile if it doesn't exist
        profile = Profile.objects.create(user=user)
    
    serializer = CurrentUserProfileSerializer(profile, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='put',
    operation_id='update_current_user_profile',
    operation_summary="Update Current User Profile",
    operation_description="""
    Update the current authenticated user's profile information.
    
    **Features:**
    - Update user fields (username, email, first_name, last_name)
    - Update profile fields (photo, date_of_birth, gender, address, etc.)
    - Update phone number (creates/updates primary mobile number)
    - Change password (requires current_password, new_password, confirm_password)
    - Supports file uploads (photo, aadhar_card, pan_card)
    
    **Password Change:**
    - If any password field is provided, all password fields are required
    - Current password must be correct
    - New password must be at least 6 characters long
    - New password and confirm password must match
    
    **File Uploads:**
    - Photo: Image file (JPG, PNG, GIF)
    - Aadhar Card: PDF or image file
    - PAN Card: PDF or image file
    
    **Phone Number:**
    - Updates or creates primary mobile number for the user
    - If a primary mobile number already exists, it will be updated
    - If no primary mobile number exists, a new one will be created
    
    **Request:**
    - All fields are optional (except password fields if changing password)
    - Use multipart/form-data for file uploads
    """,
    tags=['Profile'],
    request_body=CurrentUserProfileUpdateSerializer,
    responses={
        200: openapi.Response(
            description="Profile updated successfully",
            schema=CurrentUserProfileSerializer()
        ),
        400: openapi.Response(
            description="Validation error",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING, description='Error message')
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
@swagger_auto_schema(
    method='patch',
    operation_id='update_current_user_profile',
    operation_summary="Update Current User Profile",
    operation_description="""
    Update the current authenticated user's profile information.
    
    **Features:**
    - Update user fields (username, email, first_name, last_name)
    - Update profile fields (photo, date_of_birth, gender, address, etc.)
    - Update phone number (creates/updates primary mobile number)
    - Change password (requires current_password, new_password, confirm_password)
    - Supports file uploads (photo, aadhar_card, pan_card)
    
    **Password Change:**
    - If any password field is provided, all password fields are required
    - Current password must be correct
    - New password must be at least 6 characters long
    - New password and confirm password must match
    
    **File Uploads:**
    - Photo: Image file (JPG, PNG, GIF)
    - Aadhar Card: PDF or image file
    - PAN Card: PDF or image file
    
    **Phone Number:**
    - Updates or creates primary mobile number for the user
    - If a primary mobile number already exists, it will be updated
    - If no primary mobile number exists, a new one will be created
    
    **Request:**
    - All fields are optional (except password fields if changing password)
    - Use multipart/form-data for file uploads
    """,
    tags=['Profile'],
    request_body=CurrentUserProfileUpdateSerializer,
    responses={
        200: openapi.Response(
            description="Profile updated successfully",
            schema=CurrentUserProfileSerializer()
        ),
        400: openapi.Response(
            description="Validation error",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING, description='Error message')
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
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_current_user_profile(request):
    """
    Update current user profile endpoint
    Supports both PUT and PATCH methods
    Uses MultiPartParser and FormParser for file uploads
    """
    user = request.user
    
    try:
        profile = Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        # Create profile if it doesn't exist
        profile = Profile.objects.create(user=user)
    
    serializer = CurrentUserProfileUpdateSerializer(
        profile,
        data=request.data,
        partial=request.method == 'PATCH',
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    serializer.save()
    
    # Return updated profile
    response_serializer = CurrentUserProfileSerializer(profile, context={'request': request})
    return Response(response_serializer.data, status=status.HTTP_200_OK)
