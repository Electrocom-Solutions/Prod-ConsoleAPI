"""
Profile Views
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from .models import Profile
from .serializers import (
    CurrentUserProfileSerializer,
    CurrentUserProfileUpdateSerializer,
    ProfileCreateSerializer,
    ProfileListSerializer
)


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
    operation_id='update_current_user_profile_patch',
    operation_summary="Update Current User Profile (PATCH)",
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


@swagger_auto_schema(
    method='post',
    operation_id='create_profile',
    operation_summary="Create New Profile",
    operation_description="""
    Create a new profile with associated user.
    
    **Required Fields:**
    - first_name: First name of the user
    - email: Email address (must be unique)
    
    **Optional Fields:**
    - last_name: Last name of the user
    - phone_number: Primary phone number
    - photo: Profile photo (image file)
    - date_of_birth: Date of birth
    - gender: Gender
    - address: Street address
    - city: City
    - state: State
    - pin_code: Pin code
    - country: Country
    - aadhar_number: Aadhar card number
    - pan_number: PAN card number
    - aadhar_card: Aadhar card document file
    - pan_card: PAN card document file
    
    **What it does:**
    - Creates a new User with the provided information
    - Creates a Profile linked to the User
    - Creates a primary MobileNumber if phone_number is provided
    - Returns the created profile with user information
    
    **Request:**
    - Use multipart/form-data for file uploads
    """,
    tags=['Profile'],
    responses={
        201: openapi.Response(
            description="Profile created successfully",
            schema=CurrentUserProfileSerializer()
        ),
        400: openapi.Response(
            description="Validation error",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
        401: openapi.Response(
            description="Unauthorized",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_profile(request):
    """
    Create a new profile with user endpoint
    Supports file uploads (photo, aadhar_card, pan_card)
    """
    serializer = ProfileCreateSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    profile = serializer.save()
    
    # Return created profile
    response_serializer = CurrentUserProfileSerializer(profile, context={'request': request})
    return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ProfilePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@swagger_auto_schema(
    method='get',
    operation_id='list_profiles',
    operation_summary="List All Profiles",
    operation_description="""
    List all profiles with optional search and pagination.
    
    **Search:**
    - Search by user's first name, last name, username, email, or phone number
    - Case-insensitive search
    
    **Pagination:**
    - Default page size: 20
    - Use `page` parameter to navigate pages
    - Use `page_size` parameter to change page size (max 100)
    
    **Response:**
    Returns a paginated list of profiles with user information.
    """,
    tags=['Profile'],
    manual_parameters=[
        openapi.Parameter('search', openapi.IN_QUERY, description="Search by name, email, or phone number", type=openapi.TYPE_STRING),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Page size (max 100)", type=openapi.TYPE_INTEGER),
    ],
    responses={
        200: openapi.Response(
            description="List of profiles",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'next': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    'previous': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    'results': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    )
                }
            )
        ),
        401: openapi.Response(
            description="Unauthorized",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_profiles(request):
    """
    List all profiles with search and pagination
    """
    from Profiles.models import MobileNumber
    
    queryset = Profile.objects.select_related('user').prefetch_related('user__mobile_numbers').all()
    
    # Search functionality
    search_query = request.query_params.get('search', '').strip()
    if search_query:
        queryset = queryset.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__mobile_numbers__mobile_number__icontains=search_query)
        ).distinct()
    
    # Pagination
    paginator = ProfilePagination()
    page = paginator.paginate_queryset(queryset, request)
    
    if page is not None:
        serializer = ProfileListSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)
    
    # If no pagination
    serializer = ProfileListSerializer(queryset, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)
