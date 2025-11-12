from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import TrainingVideo
from .serializers import (
    TrainingVideoListSerializer,
    TrainingVideoDetailSerializer,
    TrainingVideoCreateUpdateSerializer
)


class TrainingVideoViewSet(viewsets.ModelViewSet):
    """
    Training Video Management APIs
    
    Permissions:
    - Staff: Can view (list, retrieve) videos
    - Superuser: Full CRUD access (create, update, delete)
    """
    queryset = TrainingVideo.objects.select_related('created_by', 'updated_by').all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return TrainingVideoListSerializer
        elif self.action in ['retrieve']:
            return TrainingVideoDetailSerializer
        return TrainingVideoCreateUpdateSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search by title
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(title__icontains=search)
        
        # Order by rank (ascending - lower rank comes first), then by creation date
        return queryset.order_by('rank', 'created_at')
    
    def get_permissions(self):
        """
        Override to check user role for different actions
        """
        if self.action in ['list', 'retrieve']:
            # Staff and superusers can view
            return [IsAuthenticated()]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Only superusers can create/update/delete
            return [IsAuthenticated()]
        return super().get_permissions()
    
    def create(self, request, *args, **kwargs):
        """Create a new training video - Superuser only"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only superusers can create training videos.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Update a training video - Superuser only"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only superusers can update training videos.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """Partially update a training video - Superuser only"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only superusers can update training videos.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().partial_update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Delete a training video - Superuser only"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only superusers can delete training videos.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='training_video_list',
        operation_summary="List All Training Videos",
        operation_description="""
        Retrieve a list of all training videos. Available to all authenticated staff and superusers.
        
        **Search Options:**
        - search: Search by video title (case-insensitive partial match)
        
        **Query Parameters:**
        - search (optional): Search by video title
        """,
        tags=['Learning Management'],
        manual_parameters=[
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description='Search by video title',
                type=openapi.TYPE_STRING,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of training videos",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'results': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT)
                        )
                    }
                )
            )
        }
    )
    def list(self, request, *args, **kwargs):
        """List all training videos"""
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='training_video_retrieve',
        operation_summary="Get Training Video Details",
        operation_description="""
        Retrieve detailed information about a specific training video.
        Available to all authenticated staff and superusers.
        """,
        tags=['Learning Management'],
        responses={
            200: TrainingVideoDetailSerializer()
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """Get training video details"""
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='training_video_create',
        operation_summary="Create Training Video",
        operation_description="""
        Create a new training video. Only superusers can create videos.
        
        **Required Fields:**
        - title: Video title
        - youtube_url: Full YouTube URL (supports various formats)
        
        **YouTube URL Formats Supported:**
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        """,
        tags=['Learning Management'],
        request_body=TrainingVideoCreateUpdateSerializer,
        responses={
            201: openapi.Response(
                description="Training video created successfully",
                schema=TrainingVideoCreateUpdateSerializer()
            ),
            403: openapi.Response(description="Forbidden - Only superusers can create videos")
        }
    )
    def create(self, request, *args, **kwargs):
        """Create a new training video - Superuser only"""
        return super().create(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='training_video_update',
        operation_summary="Update Training Video",
        operation_description="""
        Update an existing training video. Only superusers can update videos.
        All fields are optional - only provided fields will be updated.
        """,
        tags=['Learning Management'],
        request_body=TrainingVideoCreateUpdateSerializer,
        responses={
            200: openapi.Response(
                description="Training video updated successfully",
                schema=TrainingVideoCreateUpdateSerializer()
            ),
            403: openapi.Response(description="Forbidden - Only superusers can update videos")
        }
    )
    def update(self, request, *args, **kwargs):
        """Update training video - Superuser only"""
        return super().update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='training_video_delete',
        operation_summary="Delete Training Video",
        operation_description="""
        Delete a training video. Only superusers can delete videos.
        This action is permanent and cannot be undone.
        """,
        tags=['Learning Management'],
        responses={
            204: openapi.Response(description="Training video deleted successfully"),
            403: openapi.Response(description="Forbidden - Only superusers can delete videos")
        }
    )
    def destroy(self, request, *args, **kwargs):
        """Delete training video - Superuser only"""
        return super().destroy(request, *args, **kwargs)
