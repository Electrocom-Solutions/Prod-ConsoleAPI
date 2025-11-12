from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Sum, Count
from django.db.models.functions import Coalesce
from datetime import date, timedelta
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import AMC, AMCBilling
from .serializers import (
    AMCListSerializer,
    AMCDetailSerializer,
    AMCCreateSerializer,
    AMCBillingDetailsSerializer,
    AMCStatisticsSerializer,
    AMCBillingUpdateSerializer,
    AMCBillingSerializer
)


class AMCViewSet(viewsets.ModelViewSet):
    """
    AMC Management APIs
    """
    queryset = AMC.objects.select_related('client', 'created_by', 'updated_by').prefetch_related('billings').all()
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return AMCListSerializer
        elif self.action in ['retrieve']:
            return AMCDetailSerializer
        return AMCCreateSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search by AMC number or client name
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(amc_number__icontains=search) |
                Q(client__profile__user__first_name__icontains=search) |
                Q(client__profile__user__last_name__icontains=search) |
                Q(client__profile__user__username__icontains=search)
            )
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by billing cycle
        billing_cycle = self.request.query_params.get('billing_cycle', None)
        if billing_cycle:
            queryset = queryset.filter(billing_cycle=billing_cycle)
        
        # Filter by expiring days (7, 15, 30)
        expiring_days = self.request.query_params.get('expiring_days', None)
        if expiring_days:
            try:
                days = int(expiring_days)
                today = date.today()
                expiry_date = today + timedelta(days=days)
                queryset = queryset.filter(
                    status=AMC.Status.ACTIVE,
                    end_date__gte=today,
                    end_date__lte=expiry_date
                )
            except ValueError:
                pass
        
        return queryset.order_by('-created_at')
    
    @swagger_auto_schema(
        operation_id='amc_list',
        operation_summary="List All AMCs",
        operation_description="""
        Retrieve a list of all AMCs with filtering and search options.
        
        **What it returns:**
        - List of AMCs with basic information (AMC number, client, amount, dates, status)
        - Days until expiry for active AMCs
        - Client information
        
        **Search Options:**
        - search: Search by AMC number or client name (case-insensitive partial match)
        
        **Filtering Options:**
        - status: Filter by AMC status (Active, Expired, Canceled)
        - billing_cycle: Filter by billing cycle (Monthly, Quarterly, Half-yearly, Yearly)
        - expiring_days: Filter AMCs expiring within specified days (7, 15, or 30 days)
        
        **Query Parameters:**
        - search (optional): Search by AMC number or client name
        - status (optional): Filter by status
        - billing_cycle (optional): Filter by billing cycle
        - expiring_days (optional): Filter by expiring within days (7, 15, 30)
        
        **Pagination:**
        Results are paginated (20 items per page by default) and sorted by creation date (newest first).
        """,
        tags=['AMC Management'],
        manual_parameters=[
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description='Search by AMC number or client name',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                description='Filter by status (Active, Expired, Canceled)',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'billing_cycle',
                openapi.IN_QUERY,
                description='Filter by billing cycle (Monthly, Quarterly, Half-yearly, Yearly)',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'expiring_days',
                openapi.IN_QUERY,
                description='Filter AMCs expiring within days (7, 15, or 30)',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of AMCs",
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
        """List all AMCs with filtering and search"""
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='amc_retrieve',
        operation_summary="Get AMC Details",
        operation_description="""
        Retrieve detailed information about a specific AMC including all billing details.
        
        **What it returns:**
        - Complete AMC information
        - All billing records with payment details
        - Summary amounts (total, paid, outstanding)
        """,
        tags=['AMC Management'],
        responses={
            200: AMCDetailSerializer()
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """Get AMC details"""
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='amc_create',
        operation_summary="Create New AMC",
        operation_description="""
        Create a new AMC (Annual Maintenance Contract) with all required and optional information.
        
        **Required Fields:**
        - client: Client ID
        - amc_number: Unique AMC number
        - amount: AMC amount
        - start_date: Start date of the AMC
        - end_date: End date of the AMC
        - billing_cycle: Billing cycle (Monthly, Quarterly, Half-yearly, Yearly)
        - status: AMC status (Active, Expired, Canceled)
        
        **Optional Fields:**
        - notes: Additional notes or description
        
        **Validation:**
        - AMC number must be unique
        - End date must be after start date
        
        **Response:**
        Returns the created AMC with all details.
        """,
        tags=['AMC Management'],
        request_body=AMCCreateSerializer,
        responses={
            201: openapi.Response(
                description="AMC created successfully",
                schema=AMCCreateSerializer()
            )
        }
    )
    def create(self, request, *args, **kwargs):
        """Create a new AMC"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @swagger_auto_schema(
        operation_id='amc_update',
        operation_summary="Update AMC",
        operation_description="""
        Update an existing AMC's information. All fields are optional - only provided fields will be updated.
        
        **Fields:**
        Same as create endpoint - all fields are optional for update.
        
        **Response:**
        Returns the updated AMC with all details.
        """,
        tags=['AMC Management'],
        request_body=AMCCreateSerializer,
        responses={
            200: openapi.Response(
                description="AMC updated successfully",
                schema=AMCCreateSerializer()
            )
        }
    )
    def update(self, request, *args, **kwargs):
        """Update AMC information"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_id='amc_partial_update',
        operation_summary="Partial Update AMC",
        operation_description="""
        Partially update an AMC's information. Only provided fields will be updated.
        
        **Use Case:**
        Use this endpoint when you only want to update specific fields without affecting others.
        """,
        tags=['AMC Management'],
        request_body=AMCCreateSerializer,
        responses={
            200: openapi.Response(
                description="AMC partially updated successfully",
                schema=AMCCreateSerializer()
            )
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """Partially update AMC information"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='amc_delete',
        operation_summary="Delete AMC",
        operation_description="""
        Delete an AMC from the system. This action is permanent and cannot be undone.
        
        **Warning:**
        Deleting an AMC will also delete all associated billing records.
        
        **Use Case:**
        Use this endpoint when you need to permanently remove an AMC from the system.
        """,
        tags=['AMC Management'],
        responses={
            204: openapi.Response(description="AMC deleted successfully"),
            404: openapi.Response(description="AMC not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        """Delete an AMC"""
        return super().destroy(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='amc_billing_details',
        operation_summary="Get AMC Billing Details",
        operation_description="""
        Retrieve billing details for a specific AMC. This endpoint is designed for the AMC details modal in the frontend.
        
        **What it returns:**
        - **Tiles:**
          * Total Amount: Sum of all billing amounts
          * Paid: Sum of all paid billing amounts
          * Outstanding: Sum of all unpaid billing amounts
        
        - **Billing Rows:**
          * bill_number: Billing number
          * period: Period from-to (formatted as "YYYY-MM-DD to YYYY-MM-DD")
          * amount: Billing amount
          * status: Payment status (Paid/Pending)
          * payment_details: Payment date and mode (if paid)
        
        **Use Case:**
        Use this endpoint when clicking on an AMC in the frontend to show the billing details modal.
        """,
        tags=['AMC Management'],
        responses={
            200: openapi.Response(
                description="AMC billing details",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'total_amount': openapi.Schema(type=openapi.TYPE_NUMBER, description='Total amount from all bills'),
                        'paid_amount': openapi.Schema(type=openapi.TYPE_NUMBER, description='Total paid amount'),
                        'outstanding_amount': openapi.Schema(type=openapi.TYPE_NUMBER, description='Total outstanding amount'),
                        'billings': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT),
                            description='List of all billing records'
                        )
                    }
                )
            )
        }
    )
    @action(detail=True, methods=['get'], url_path='billing-details')
    def billing_details(self, request, pk=None):
        """Get AMC billing details for modal"""
        amc = self.get_object()
        
        # Calculate totals
        total_amount = amc.billings.aggregate(total=Sum('amount'))['total'] or 0
        paid_amount = amc.billings.filter(paid=True).aggregate(total=Sum('amount'))['total'] or 0
        outstanding_amount = amc.billings.filter(paid=False).aggregate(total=Sum('amount'))['total'] or 0
        
        # Serialize billings
        billings_serializer = AMCBillingSerializer(amc.billings.all(), many=True)
        
        data = {
            'total_amount': float(total_amount),
            'paid_amount': float(paid_amount),
            'outstanding_amount': float(outstanding_amount),
            'billings': billings_serializer.data
        }
        
        serializer = AMCBillingDetailsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_id='amc_expiring_count',
        operation_summary="Get Count of AMCs Expiring in Next 30 Days",
        operation_description="""
        Get the count of AMCs that are expiring within the next 30 days.
        
        **What it returns:**
        - count: Number of AMCs expiring in next 30 days
        
        **Use Case:**
        Use this endpoint to get a quick count of AMCs that need attention soon.
        """,
        tags=['AMC Management'],
        responses={
            200: openapi.Response(
                description="Count of expiring AMCs",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of AMCs expiring in next 30 days')
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['get'], url_path='expiring-count')
    def expiring_count(self, request):
        """Get count of AMCs expiring in next 30 days"""
        today = date.today()
        expiry_date = today + timedelta(days=30)
        
        count = AMC.objects.filter(
            status=AMC.Status.ACTIVE,
            end_date__gte=today,
            end_date__lte=expiry_date
        ).count()
        
        return Response({'count': count}, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_id='amc_statistics',
        operation_summary="Get AMC Management Statistics",
        operation_description="""
        Retrieve statistics for the AMC management dashboard.
        
        **What it returns:**
        - total_amcs: Total number of AMCs in the system
        - active_amcs: Number of active AMCs
        - expiring_soon: Number of AMCs expiring within next 30 days
        - pending_bills: Number of unpaid billing records
        
        **Use Case:**
        Use this endpoint to populate dashboard tiles showing key metrics for AMC management.
        """,
        tags=['AMC Management'],
        responses={
            200: openapi.Response(
                description="AMC management statistics",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'total_amcs': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total number of AMCs'),
                        'active_amcs': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of active AMCs'),
                        'expiring_soon': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of AMCs expiring in next 30 days'),
                        'pending_bills': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of unpaid bills')
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """Get AMC management statistics for dashboard"""
        today = date.today()
        expiry_date = today + timedelta(days=30)
        
        # Total AMCs
        total_amcs = AMC.objects.count()
        
        # Active AMCs
        active_amcs = AMC.objects.filter(status=AMC.Status.ACTIVE).count()
        
        # Expiring soon (next 30 days)
        expiring_soon = AMC.objects.filter(
            status=AMC.Status.ACTIVE,
            end_date__gte=today,
            end_date__lte=expiry_date
        ).count()
        
        # Pending bills
        pending_bills = AMCBilling.objects.filter(paid=False).count()
        
        data = {
            'total_amcs': total_amcs,
            'active_amcs': active_amcs,
            'expiring_soon': expiring_soon,
            'pending_bills': pending_bills
        }
        
        serializer = AMCStatisticsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_id='amc_billing_update',
        operation_summary="Update AMC Billing Payment Status",
        operation_description="""
        Update the payment status of an AMC billing record.
        
        **Fields:**
        - paid: Boolean indicating if the bill is paid
        - payment_date: Date of payment (required if paid=True)
        - payment_mode: Payment mode (Cash, Bank Transfer, Cheque, UPI) (required if paid=True)
        - notes: Optional notes about the payment
        
        **Use Case:**
        Use this endpoint to mark bills as paid or pending in the billing details modal.
        """,
        tags=['AMC Management'],
        request_body=AMCBillingUpdateSerializer,
        responses={
            200: openapi.Response(
                description="Billing record updated successfully",
                schema=AMCBillingSerializer()
            ),
            404: openapi.Response(description="Billing record not found")
        }
    )
    @action(detail=False, methods=['patch'], url_path='billing/(?P<billing_id>[^/.]+)/update')
    def update_billing(self, request, billing_id=None):
        """Update AMC billing payment status"""
        try:
            billing = AMCBilling.objects.get(id=billing_id)
        except AMCBilling.DoesNotExist:
            return Response(
                {'error': 'Billing record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = AMCBillingUpdateSerializer(
            billing,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Return updated billing with full details
        billing_serializer = AMCBillingSerializer(billing)
        return Response(billing_serializer.data, status=status.HTTP_200_OK)
