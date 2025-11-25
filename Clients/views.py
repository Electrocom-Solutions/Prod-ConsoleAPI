from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q, Sum, Count, DecimalField, Value
from django.db.models.functions import Coalesce
from datetime import date
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Client, Firm
from .serializers import (
    ClientListSerializer,
    ClientDetailSerializer,
    ClientCreateUpdateSerializer,
    ClientStatisticsSerializer,
    FirmListSerializer,
    FirmDetailSerializer,
    FirmCreateUpdateSerializer
)
from AMC.models import AMC, AMCBilling
from Projects.models import Project


class ClientViewSet(viewsets.ModelViewSet):
    """
    Client Management APIs
    """
    queryset = Client.objects.select_related('profile', 'profile__user', 'created_by', 'updated_by').prefetch_related('amcs').all()
    parser_classes = [MultiPartParser, FormParser]
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return ClientListSerializer
        elif self.action in ['retrieve']:
            return ClientDetailSerializer
        return ClientCreateUpdateSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search by name (first_name, last_name from profile.user) or phone_number
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(profile__user__first_name__icontains=search) |
                Q(profile__user__last_name__icontains=search) |
                Q(profile__user__email__icontains=search) |
                Q(phone_number__icontains=search) |
                Q(primary_contact_name__icontains=search)
            )
        
        # Filter by has_active_amc
        has_active_amc = self.request.query_params.get('has_active_amc', None)
        if has_active_amc is not None:
            has_active_amc = has_active_amc.lower() in ['true', '1', 'yes']
            if has_active_amc:
                queryset = queryset.filter(amcs__status=AMC.Status.ACTIVE).distinct()
            else:
                queryset = queryset.exclude(amcs__status=AMC.Status.ACTIVE)
        
        return queryset.order_by('-created_at')
    
    @swagger_auto_schema(
        operation_id='client_list',
        operation_summary="List All Clients",
        operation_description="""
        Retrieve a list of all clients with basic information and filtering options.
        
        **What it returns:**
        - List of clients with basic information (name, email, phone)
        - Indicates if client has active AMC
        - Created date
        
        **Search Options:**
        - search: Search by client name (first name, last name) or phone number (case-insensitive partial match)
        
        **Filtering Options:**
        - has_active_amc: Filter clients by whether they have active AMC (true/false)
        
        **Query Parameters:**
        - search (optional): Search by name or phone number
        - has_active_amc (optional): Filter by active AMC status (true/false)
        
        **Pagination:**
        Results are paginated (20 items per page by default) and sorted by creation date (newest first).
        """,
        tags=['Client Management'],
        manual_parameters=[
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description='Search by client name (first name, last name) or phone number',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'has_active_amc',
                openapi.IN_QUERY,
                description='Filter by active AMC status (true/false)',
                type=openapi.TYPE_BOOLEAN,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of clients",
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
        """List all clients with filtering and search"""
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='client_retrieve',
        operation_summary="Get Client Details",
        operation_description="""
        Retrieve detailed information about a specific client including all personal and professional details.
        
        **What it returns:**
        - Complete client information including personal details, contact information
        - Professional information (designation, joining date, salary)
        - Photo URL
        - Identification numbers (Aadhar, PAN)
        - Aadhar card and PAN card file URLs (from Profile model)
        - Profile information (address, city, state, etc. are in Profile model)
        - Creation and update timestamps
        """,
        tags=['Client Management'],
        responses={
            200: ClientDetailSerializer()
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """Get client details"""
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='client_create',
        operation_summary="Create New Client",
        operation_description="""
        Create a new client with all required and optional information.
        
        **Required Fields:**
        - first_name: Client's first name
        - last_name: Client's last name
        
        **Optional Fields:**
        - email: Client's email address
        - phone_number: Client's phone number
        - photo: Client's photo (image file)
        - date_of_birth: Date of birth
        - gender: Gender (Male/Female)
        - aadhar_number: Aadhar card number
        - pan_number: PAN card number
        - aadhar_card: Aadhar card document file (will be saved in Profile model)
        - pan_card: PAN card document file (will be saved in Profile model)
        - designation: Designation (Technician, Field Staff, Computer Operator)
        - joining_date: Date of joining
        - monthly_salary: Monthly salary amount
        - notes: Additional notes
        - profile: Profile ID (if linking to existing profile, otherwise profile will be created)
        
        **Note:** 
        - Address, city, state, pin_code, and country are now stored in the Profile model, not in Client model.
        - Aadhar card and PAN card files are stored in the Profile model, not in Client model.
        
        **Response:**
        Returns the created client with all details including aadhar_card_url and pan_card_url.
        """,
        tags=['Client Management'],
        responses={
            201: openapi.Response(
                description="Client created successfully",
                schema=ClientCreateUpdateSerializer()
            )
        }
    )
    def create(self, request, *args, **kwargs):
        """Create a new client"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @swagger_auto_schema(
        operation_id='client_update',
        operation_summary="Update Client",
        operation_description="""
        Update an existing client's information. All fields are optional - only provided fields will be updated.
        
        **Fields:**
        Same as create endpoint - all fields are optional for update.
        
        **Response:**
        Returns the updated client with all details.
        """,
        tags=['Client Management'],
        responses={
            200: openapi.Response(
                description="Client updated successfully",
                schema=ClientCreateUpdateSerializer()
            )
        }
    )
    def update(self, request, *args, **kwargs):
        """Update client information"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_id='client_partial_update',
        operation_summary="Partial Update Client",
        operation_description="""
        Partially update a client's information. Only provided fields will be updated.
        
        **Use Case:**
        Use this endpoint when you only want to update specific fields without affecting others.
        """,
        tags=['Client Management'],
        responses={
            200: openapi.Response(
                description="Client partially updated successfully",
                schema=ClientCreateUpdateSerializer()
            )
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """Partially update client information"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='client_delete',
        operation_summary="Delete Client",
        operation_description="""
        Delete a client from the system. This action is permanent and cannot be undone.
        
        **Warning:**
        Deleting a client will also delete all associated data including:
        - All AMCs associated with the client
        - All projects associated with the client
        - All related records
        
        **Use Case:**
        Use this endpoint when you need to permanently remove a client from the system.
        Consider using soft delete or archiving if you need to preserve historical data.
        """,
        tags=['Client Management'],
        responses={
            204: openapi.Response(description="Client deleted successfully"),
            404: openapi.Response(description="Client not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        """Delete a client and its associated profile and user if they have no other references"""
        from django.db import transaction
        from Profiles.models import Profile
        from django.contrib.auth.models import User
        
        instance = self.get_object()
        profile = instance.profile
        user = profile.user if profile else None
        client_id = instance.id
        profile_id = profile.id if profile else None
        
        with transaction.atomic():
            # Check if profile has other clients before deleting
            if profile:
                other_clients = Client.objects.filter(profile=profile).exclude(id=client_id).exists()
                
                # Delete the client first
                super().destroy(request, *args, **kwargs)
                
                # If no other clients, delete the profile and user
                if not other_clients:
                    if user:
                        # Check if user has other profiles
                        other_profiles = Profile.objects.filter(user=user).exclude(id=profile_id).exists()
                        if not other_profiles:
                            # Delete user (this will cascade delete the profile due to CASCADE relationship)
                            user.delete()
                        else:
                            # User has other profiles, so only delete this profile
                            profile.delete()
                    else:
                        # No user, so just delete the profile
                        profile.delete()
            else:
                # Delete the client if no profile
                super().destroy(request, *args, **kwargs)
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @swagger_auto_schema(
        operation_id='client_statistics',
        operation_summary="Get Client Management Statistics",
        operation_description="""
        Retrieve statistics for the client management dashboard.
        
        **What it returns:**
        - total_clients: Total number of clients in the system
        - active_amcs_count: Number of active AMCs
        - open_projects_count: Number of open projects (status: Planned, In Progress, On Hold)
        - outstanding_amount: Total outstanding amount from clients (unpaid AMC bills)
        
        **Outstanding Amount Calculation:**
        The outstanding amount is calculated as the sum of all unpaid AMC billing amounts.
        This represents the total money that needs to be collected from clients for AMC services.
        Example: If a client has an AMC with quarterly billing and 2 quarters have passed with 
        only the first quarter paid, the outstanding amount for the second quarter will be included.
        
        **Use Case:**
        Use this endpoint to populate dashboard tiles showing key metrics for client management.
        """,
        tags=['Client Management'],
        responses={
            200: openapi.Response(
                description="Client management statistics",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'total_clients': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total number of clients'),
                        'active_amcs_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of active AMCs'),
                        'open_projects_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of open projects'),
                        'outstanding_amount': openapi.Schema(type=openapi.TYPE_NUMBER, description='Total outstanding amount (₹)')
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """Get client management statistics for dashboard"""
        # Total clients
        total_clients = Client.objects.count()
        
        # Active AMCs
        active_amcs_count = AMC.objects.filter(status=AMC.Status.ACTIVE).count()
        
        # Open projects (Planned, In Progress, On Hold)
        open_projects_count = Project.objects.filter(
            status__in=[Project.Status.PLANNED, Project.Status.IN_PROGRESS, Project.Status.ON_HOLD]
        ).count()
        
        # Outstanding amount (unpaid AMC bills)
        # Use output_field to specify DecimalField to avoid mixed type error
        # Value(0) with output_field ensures the default value matches the DecimalField type
        outstanding_amount = AMCBilling.objects.filter(
            paid=False
        ).aggregate(
            total=Coalesce(
                Sum('amount'), 
                Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        )['total'] or 0
        
        data = {
            'total_clients': total_clients,
            'active_amcs_count': active_amcs_count,
            'open_projects_count': open_projects_count,
            'outstanding_amount': outstanding_amount
        }
        
        serializer = ClientStatisticsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class FirmViewSet(viewsets.ModelViewSet):
    """
    Firm Management APIs (Settings Module)
    """
    queryset = Firm.objects.select_related(
        'firm_owner_profile', 'firm_owner_profile__user',
        'created_by', 'updated_by'
    ).all()
    
    # Ensure we have proper error handling
    def get_queryset(self):
        """Return firms with search and filtering"""
        try:
            queryset = Firm.objects.select_related(
                'firm_owner_profile', 'firm_owner_profile__user',
                'created_by', 'updated_by'
            ).all()
            
            # Search by firm name, GST number, PAN number, email, mobile, or owner name
            search = self.request.query_params.get('search', None)
            if search:
                queryset = queryset.filter(
                    Q(firm_name__icontains=search) |
                    Q(gst_number__icontains=search) |
                    Q(pan_number__icontains=search) |
                    Q(official_email__icontains=search) |
                    Q(official_mobile_number__icontains=search) |
                    Q(address__icontains=search) |
                    Q(firm_owner_profile__user__first_name__icontains=search) |
                    Q(firm_owner_profile__user__last_name__icontains=search) |
                    Q(firm_owner_profile__user__username__icontains=search)
                )
            
            # Filter by firm type
            firm_type_filter = self.request.query_params.get('firm_type', None)
            if firm_type_filter:
                queryset = queryset.filter(firm_type=firm_type_filter)
            
            return queryset.order_by('-created_at')
        except Exception as e:
            import traceback
            print(f"Error in FirmViewSet.get_queryset: {str(e)}")
            print(traceback.format_exc())
            # Return empty queryset on error to prevent 500
            return Firm.objects.none()
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return FirmListSerializer
        elif self.action in ['retrieve']:
            return FirmDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return FirmCreateUpdateSerializer
        return FirmListSerializer
    
    @swagger_auto_schema(
        operation_id='firm_list',
        operation_summary="Get List of All Firms",
        operation_description="""
        Retrieve a list of all firms in the system.
        
        **What it returns:**
        - List of firms with basic information (name, type, owner, email, mobile, GST, PAN)
        
        **Search Options:**
        - search: Search by firm name, GST number, PAN number, email, mobile, address, or owner name (case-insensitive partial match)
        
        **Filter Options:**
        - firm_type: Filter by firm type (Proprietorship, Partnership, Pvt Ltd, LLP)
        
        **Query Parameters:**
        - search (optional): Search by firm name, GST number, PAN number, email, mobile, address, or owner name
        - firm_type (optional): Filter by firm type (Proprietorship, Partnership, Pvt Ltd, LLP)
        
        **Pagination:**
        Results are paginated (20 items per page by default) and sorted by creation date (newest first).
        """,
        tags=['Settings Module'],
        manual_parameters=[
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description='Search by firm name, GST number, PAN number, email, mobile, address, or owner name',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'firm_type',
                openapi.IN_QUERY,
                description='Filter by firm type',
                type=openapi.TYPE_STRING,
                enum=['Proprietorship', 'Partnership', 'Pvt Ltd', 'LLP'],
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of firms",
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
        """Get list of all firms"""
        try:
            return super().list(request, *args, **kwargs)
        except Exception as e:
            import traceback
            print(f"Error in FirmViewSet.list: {str(e)}")
            print(traceback.format_exc())
            raise
    
    @swagger_auto_schema(
        operation_id='firm_retrieve',
        operation_summary="Get Firm Details",
        operation_description="""
        Retrieve detailed information about a specific firm.
        
        **What it returns:**
        - Complete firm information including all fields and owner details
        """,
        tags=['Settings Module'],
        responses={
            200: FirmDetailSerializer(),
            404: openapi.Response(description="Firm not found")
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """Get firm details"""
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='firm_create',
        operation_summary="Add New Firm",
        operation_description="""
        Create a new firm entry.
        
        **Required Fields:**
        - firm_name: Firm Name
        
        **Optional Fields:**
        - firm_type: Firm Type (Proprietorship, Partnership, Pvt Ltd, LLP)
        - firm_owner_profile: Firm Owner Profile ID (dropdown - FK to Profile)
        - official_email: Firm Official Email
        - official_mobile_number: Firm Official Mobile Number
        - address: Address
        - gst_number: GST Number
        - pan_number: PAN Number
        
        **Response:**
        Returns the created firm entry.
        """,
        tags=['Settings Module'],
        request_body=FirmCreateUpdateSerializer,
        responses={
            201: openapi.Response(
                description="Firm created successfully",
                schema=FirmCreateUpdateSerializer()
            ),
            400: openapi.Response(description="Invalid request data")
        }
    )
    def create(self, request, *args, **kwargs):
        """Create a new firm"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @swagger_auto_schema(
        operation_id='firm_update',
        operation_summary="Update Firm",
        operation_description="""
        Update an existing firm's information. All fields are optional - only provided fields will be updated.
        
        **Fields:**
        Same as create endpoint - all fields are optional for update.
        
        **Response:**
        Returns the updated firm entry.
        """,
        tags=['Settings Module'],
        request_body=FirmCreateUpdateSerializer,
        responses={
            200: openapi.Response(
                description="Firm updated successfully",
                schema=FirmCreateUpdateSerializer()
            )
        }
    )
    def update(self, request, *args, **kwargs):
        """Update firm information"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_id='firm_partial_update',
        operation_summary="Partial Update Firm",
        operation_description="""
        Partially update a firm's information. Only provided fields will be updated.
        """,
        tags=['Settings Module'],
        request_body=FirmCreateUpdateSerializer,
        responses={
            200: openapi.Response(
                description="Firm partially updated successfully",
                schema=FirmCreateUpdateSerializer()
            )
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """Partially update firm information"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='firm_delete',
        operation_summary="Delete Firm",
        operation_description="""
        Delete a firm from the system. This action is permanent and cannot be undone.
        
        **Warning:**
        Deleting a firm will affect all related records that reference this firm.
        
        **Use Case:**
        Use this endpoint when you need to permanently remove a firm from the system.
        """,
        tags=['Settings Module'],
        responses={
            204: openapi.Response(description="Firm deleted successfully"),
            404: openapi.Response(description="Firm not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        """Delete a firm"""
        return super().destroy(request, *args, **kwargs)
