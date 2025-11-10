from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import datetime, timedelta
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from Clients.models import Client
from AMC.models import AMC
from Tenders.models import Tender
from Tasks.models import Task
from Analytics.models import ActivityLog
from Analytics.serializers import (
    DashboardStatsSerializer,
    ExpiringAMCSerializer,
    RecentActivitySerializer
)


class DashboardViewSet(viewsets.ViewSet):
    """
    Dashboard APIs for getting statistics and data
    """
    
    def _get_counts(self):
        """Helper method to get all counts - removes code duplication"""
        return {
            'total_clients': Client.objects.count(),
            'active_amcs_count': AMC.objects.filter(status=AMC.Status.ACTIVE).count(),
            'active_tenders_count': Tender.objects.filter(status__in=[Tender.Status.FILED, Tender.Status.AWARDED]).count(),
            'in_progress_tasks_count': Task.objects.filter(status=Task.Status.IN_PROGRESS).count()
        }
    
    def _get_expiring_amcs(self, limit=2):
        """Helper method to get expiring AMCs - removes code duplication"""
        today = datetime.now().date()
        expiry_date = today + timedelta(days=30)
        
        expiring_amcs = AMC.objects.filter(
            status=AMC.Status.ACTIVE,
            end_date__gte=today,
            end_date__lte=expiry_date
        ).select_related('client').order_by('end_date')[:limit]
        
        result = []
        for amc in expiring_amcs:
            days_until_expiry = (amc.end_date - today).days
            result.append({
                'client_name': amc.client.full_name,
                'amc_expiry_date': amc.end_date,
                'expiry_count_days': days_until_expiry,
                'amc_number': amc.amc_number
            })
        
        return result
    
    def _get_recent_activities_queryset(self, limit=3):
        """Helper method to get recent activities queryset - removes code duplication"""
        return ActivityLog.objects.select_related('created_by').order_by('-created_at')[:limit]
    
    @swagger_auto_schema(
        operation_id='dashboard_recent_activities',
        operation_summary="Get Recent Activities",
        operation_description="Get 3 most recent activities",
        tags=['Dashboard'],
        responses={200: openapi.Response(
            description="Recent activities list",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'recent_activities': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'entity_type': openapi.Schema(type=openapi.TYPE_STRING),
                                'entity_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'action': openapi.Schema(type=openapi.TYPE_STRING),
                                'description': openapi.Schema(type=openapi.TYPE_STRING),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                'created_by': openapi.Schema(type=openapi.TYPE_INTEGER, x_nullable=True),
                                'created_by_username': openapi.Schema(type=openapi.TYPE_STRING, x_nullable=True)
                            }
                        )
                    )
                }
            )
        )}
    )
    @action(detail=False, methods=['get'], url_path='recent-activities')
    def recent_activities(self, request):
        """Get 3 most recent activities"""
        activities = self._get_recent_activities_queryset(limit=3)
        serializer = RecentActivitySerializer(activities, many=True)
        return Response({'recent_activities': serializer.data})
    
    @swagger_auto_schema(
        operation_id='dashboard_all_stats',
        operation_summary="Get All Dashboard Statistics",
        operation_description="Get all dashboard statistics in one API call (counts, expiring AMCs, and recent activities)",
        tags=['Dashboard'],
        responses={200: openapi.Response(
            description="Complete dashboard statistics",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'total_clients': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'active_amcs_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'active_tenders_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'in_progress_tasks_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'expiring_amcs': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'client_name': openapi.Schema(type=openapi.TYPE_STRING),
                                'amc_expiry_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                                'expiry_count_days': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'amc_number': openapi.Schema(type=openapi.TYPE_STRING)
                            }
                        )
                    ),
                    'recent_activities': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    )
                }
            )
        )}
    )
    @action(detail=False, methods=['get'], url_path='all-stats')
    def all_stats(self, request):
        """Get all dashboard statistics in one API call"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            counts = self._get_counts()
            expiring_amcs_data = self._get_expiring_amcs(limit=2)
            activities = self._get_recent_activities_queryset(limit=3)
            
            # Serialize activities separately to ensure proper serialization of User objects
            # This ensures created_by is serialized as an integer ID, not a User object
            activities_serializer = RecentActivitySerializer(activities, many=True)
            # Convert to list to ensure all data is fully evaluated and serialized
            activities_data = list(activities_serializer.data)
            
            # Build response data - ensure all values are JSON-serializable
            data = {
                'total_clients': int(counts['total_clients']),
                'active_amcs_count': int(counts['active_amcs_count']),
                'active_tenders_count': int(counts['active_tenders_count']),
                'in_progress_tasks_count': int(counts['in_progress_tasks_count']),
                'expiring_amcs': expiring_amcs_data,
                'recent_activities': activities_data
            }
            
            # Return the data directly - activities are already properly serialized
            # All User objects should be converted to integer IDs by the serializer
            return Response(data)
        except Exception as e:
            # Log the error and return a safe response
            logger.error(f"Error in all_stats endpoint: {str(e)}", exc_info=True)
            # Return basic stats even if activities fail
            try:
                counts = self._get_counts()
                expiring_amcs_data = self._get_expiring_amcs(limit=2)
                return Response({
                    **counts,
                    'expiring_amcs': expiring_amcs_data,
                    'recent_activities': []
                })
            except Exception as inner_e:
                logger.error(f"Error getting fallback stats: {str(inner_e)}", exc_info=True)
                return Response({
                    'total_clients': 0,
                    'active_amcs_count': 0,
                    'active_tenders_count': 0,
                    'in_progress_tasks_count': 0,
                    'expiring_amcs': [],
                    'recent_activities': []
                }, status=500)
