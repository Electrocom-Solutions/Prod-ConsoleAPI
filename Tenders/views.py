from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.db import transaction
from django.http import FileResponse
from urllib.parse import quote
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Tender, TenderDeposit, TenderDocument
from .serializers import (
    TenderListSerializer,
    TenderDetailSerializer,
    TenderCreateSerializer,
    TenderStatisticsSerializer,
    TenderDocumentSerializer,
    TenderDocumentUploadSerializer,
    ActivityFeedSerializer
)
from Analytics.models import ActivityLog


class TenderViewSet(viewsets.ModelViewSet):
    """
    Tender Management APIs
    """
    queryset = Tender.objects.select_related('created_by', 'updated_by').prefetch_related('deposits', 'documents', 'documents__created_by').all()
    parser_classes = [MultiPartParser, FormParser]
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return TenderListSerializer
        elif self.action in ['retrieve']:
            return TenderDetailSerializer
        return TenderCreateSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search by tender name or reference number
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(reference_number__icontains=search)
            )
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by pending EMDs
        pending_emds = self.request.query_params.get('pending_emds', None)
        if pending_emds and pending_emds.lower() in ['true', '1', 'yes']:
            # Pending EMDs: Tenders in Closed or Lost status
            queryset = queryset.filter(status__in=[Tender.Status.CLOSED, Tender.Status.LOST])
        
        return queryset.order_by('-created_at')
    
    def _calculate_pending_emd_for_tender(self, tender):
        """Calculate pending EMD amount for a tender based on status"""
        if tender.status == Tender.Status.CLOSED:
            # Closed: collect whole EMD (Security Deposit 1 + Security Deposit 2)
            total = tender.deposits.aggregate(total=Sum('dd_amount'))['total']
            return float(total) if total else 0.0
        elif tender.status == Tender.Status.LOST:
            # Lost: collect only Security Deposit 1
            deposit1 = tender.deposits.filter(
                deposit_type=TenderDeposit.DepositType.EMD_SECURITY1
            ).first()
            return float(deposit1.dd_amount) if deposit1 else 0.0
        return 0.0
    
    @swagger_auto_schema(
        operation_id='tender_list',
        operation_summary="List All Tenders",
        operation_description="""
        Retrieve a list of all tenders with filtering and search options.
        
        **What it returns:**
        - List of tenders with basic information (name, reference number, dates, status, value)
        - EMD information (total EMD cost, security deposits, pending EMD amount)
        - Indicates if tender has pending EMD
        
        **Search Options:**
        - search: Search by tender name or reference number (case-insensitive partial match)
        
        **Filtering Options:**
        - status: Filter by tender status (Filed, Awarded, Lost, Closed)
        - pending_emds: Filter tenders with pending EMDs (true/false)
          * Pending EMDs are tenders in "Closed" or "Lost" status
          * Closed tenders: collect whole EMD (Security Deposit 1 + Security Deposit 2)
          * Lost tenders: collect only Security Deposit 1
        
        **Query Parameters:**
        - search (optional): Search by tender name or reference number
        - status (optional): Filter by status (Filed, Awarded, Lost, Closed)
        - pending_emds (optional): Filter by pending EMDs (true/false)
        
        **Pagination:**
        Results are paginated (20 items per page by default) and sorted by creation date (newest first).
        """,
        tags=['Tender Management'],
        manual_parameters=[
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description='Search by tender name or reference number',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                description='Filter by status (Filed, Awarded, Lost, Closed)',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'pending_emds',
                openapi.IN_QUERY,
                description='Filter tenders with pending EMDs (true/false). Pending EMDs are tenders in Closed or Lost status.',
                type=openapi.TYPE_BOOLEAN,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of tenders",
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
        """List all tenders with filtering and search"""
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='tender_retrieve',
        operation_summary="Get Tender Details",
        operation_description="""
        Retrieve detailed information about a specific tender including all related fields, deposits, documents, and activity feed.
        
        **What it returns:**
        - Complete tender information (Tender Name, Reference Number, Description, Filed Date, Start Date, End Date, Estimated Value, Status)
        - Security Deposit 1 details (DD Date, DD Number, DD Amount, DD Bank Name, DD Beneficiary Name)
        - Security Deposit 2 details (DD Date, DD Number, DD Amount, DD Bank Name, DD Beneficiary Name)
        - EMD calculations (total EMD cost, security deposit 1 amount, security deposit 2 amount, pending EMD amount)
        - All documents attached to the tender (from TenderDocument table)
        - Activity feed for the tender (all activities related to this tender)
        
        **Use Case:**
        Use this endpoint to display complete tender information in the tender detail page, including all related documents and activity history.
        """,
        tags=['Tender Management'],
        responses={
            200: TenderDetailSerializer()
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """Get tender details"""
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='tender_create',
        operation_summary="Create New Tender",
        operation_description="""
        Create a new tender with all required and optional information including security deposits.
        
        **Required Fields:**
        - name: Tender name
        
        **Optional Fields:**
        - reference_number: Tender reference number
        - description: Tender description
        - filed_date: Date when tender was filed
        - start_date: Tender start date
        - end_date: Tender end date
        - estimated_value: Estimated value of the tender
        - status: Tender status (Filed, Awarded, Lost, Closed)
        
        **Security Deposit Fields (Optional):**
        - security_deposit_1_dd_date: DD date for Security Deposit 1
        - security_deposit_1_dd_number: DD number for Security Deposit 1
        - security_deposit_1_dd_amount: DD amount for Security Deposit 1
        - security_deposit_1_dd_bank_name: Bank name for Security Deposit 1
        - security_deposit_1_dd_beneficiary_name: Beneficiary name for Security Deposit 1
        - security_deposit_2_dd_date: DD date for Security Deposit 2
        - security_deposit_2_dd_number: DD number for Security Deposit 2
        - security_deposit_2_dd_amount: DD amount for Security Deposit 2
        - security_deposit_2_dd_bank_name: Bank name for Security Deposit 2
        - security_deposit_2_dd_beneficiary_name: Beneficiary name for Security Deposit 2
        
        **Response:**
        Returns the created tender with all details.
        """,
        tags=['Tender Management'],
        request_body=TenderCreateSerializer,
        responses={
            201: openapi.Response(
                description="Tender created successfully",
                schema=TenderCreateSerializer()
            )
        }
    )
    def create(self, request, *args, **kwargs):
        """Create a new tender"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @swagger_auto_schema(
        operation_id='tender_update',
        operation_summary="Update Tender",
        operation_description="""
        Update an existing tender's information including security deposits. All fields are optional - only provided fields will be updated.
        
        **Fields:**
        Same as create endpoint - all fields are optional for update.
        Security deposit fields will update existing deposits or create new ones if they don't exist.
        
        **Response:**
        Returns the updated tender with all details.
        """,
        tags=['Tender Management'],
        request_body=TenderCreateSerializer,
        responses={
            200: openapi.Response(
                description="Tender updated successfully",
                schema=TenderCreateSerializer()
            )
        }
    )
    def update(self, request, *args, **kwargs):
        """Update tender information"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_id='tender_partial_update',
        operation_summary="Partial Update Tender",
        operation_description="""
        Partially update a tender's information. Only provided fields will be updated.
        
        **Use Case:**
        Use this endpoint when you only want to update specific fields without affecting others.
        """,
        tags=['Tender Management'],
        request_body=TenderCreateSerializer,
        responses={
            200: openapi.Response(
                description="Tender partially updated successfully",
                schema=TenderCreateSerializer()
            )
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """Partially update tender information"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='tender_delete',
        operation_summary="Delete Tender",
        operation_description="""
        Delete a tender from the system. This action is permanent and cannot be undone.
        
        **Warning:**
        Deleting a tender will also delete all associated deposits and documents.
        
        **Use Case:**
        Use this endpoint when you need to permanently remove a tender from the system.
        """,
        tags=['Tender Management'],
        responses={
            204: openapi.Response(description="Tender deleted successfully"),
            404: openapi.Response(description="Tender not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        """Delete a tender"""
        return super().destroy(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='tender_statistics',
        operation_summary="Get Tender Management Statistics",
        operation_description="""
        Retrieve statistics for the tender management dashboard.
        
        **What it returns:**
        - total_tenders: Total number of tenders in the system
        - tenders_filed: Number of tenders with "Filed" status
        - tenders_awarded: Number of tenders with "Awarded" status
        - total_value_awarded: Total value (₹) of all awarded tenders
        - pending_emds: Number of tenders with pending EMDs (Closed or Lost status)
        - pending_emd_amount: Total pending EMD amount (₹)
        
        **Pending EMD Calculation:**
        - Pending EMDs are tenders in "Closed" or "Lost" status
        - Closed tenders: pending amount = Security Deposit 1 + Security Deposit 2
        - Lost tenders: pending amount = Security Deposit 1 only
        
        **Use Case:**
        Use this endpoint to populate dashboard tiles showing key metrics for tender management.
        """,
        tags=['Tender Management'],
        responses={
            200: openapi.Response(
                description="Tender management statistics",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'total_tenders': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total number of tenders'),
                        'tenders_filed': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of tenders filed'),
                        'tenders_awarded': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of tenders awarded'),
                        'total_value_awarded': openapi.Schema(type=openapi.TYPE_NUMBER, description='Total value of awarded tenders (₹)'),
                        'pending_emds': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of tenders with pending EMDs'),
                        'pending_emd_amount': openapi.Schema(type=openapi.TYPE_NUMBER, description='Total pending EMD amount (₹)')
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """Get tender management statistics for dashboard"""
        # Total tenders
        total_tenders = Tender.objects.count()
        
        # Tenders filed
        tenders_filed = Tender.objects.filter(status=Tender.Status.FILED).count()
        
        # Tenders awarded
        tenders_awarded = Tender.objects.filter(status=Tender.Status.AWARDED).count()
        
        # Total value of awarded tenders
        total_value_awarded = Tender.objects.filter(
            status=Tender.Status.AWARDED
        ).aggregate(
            total=Coalesce(Sum('estimated_value'), 0)
        )['total'] or 0
        
        # Pending EMDs: Tenders in Closed or Lost status
        pending_emd_tenders = Tender.objects.filter(
            status__in=[Tender.Status.CLOSED, Tender.Status.LOST]
        )
        pending_emds_count = pending_emd_tenders.count()
        
        # Calculate pending EMD amount
        pending_emd_amount = 0.0
        for tender in pending_emd_tenders:
            if tender.status == Tender.Status.CLOSED:
                # Closed: collect whole EMD (Security Deposit 1 + Security Deposit 2)
                total = tender.deposits.aggregate(total=Sum('dd_amount'))['total']
                pending_emd_amount += float(total) if total else 0.0
            elif tender.status == Tender.Status.LOST:
                # Lost: collect only Security Deposit 1
                deposit1 = tender.deposits.filter(
                    deposit_type=TenderDeposit.DepositType.EMD_SECURITY1
                ).first()
                if deposit1:
                    pending_emd_amount += float(deposit1.dd_amount)
        
        data = {
            'total_tenders': total_tenders,
            'tenders_filed': tenders_filed,
            'tenders_awarded': tenders_awarded,
            'total_value_awarded': float(total_value_awarded),
            'pending_emds': pending_emds_count,
            'pending_emd_amount': pending_emd_amount
        }
        
        serializer = TenderStatisticsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_id='tender_attach_document',
        operation_summary="Attach Document to Tender",
        operation_description="""
        Attach a document to a tender. These documents are stored in the TenderDocument table and are used for reference purposes only.
        
        **Note:**
        These documents are separate from the Document Management module. They are specific to this tender and used for reference.
        
        **Request Fields:**
        - file (required): Document file to upload
        - description (optional): Description or notes about the document
        
        **Response:**
        Returns the created document record with file URL.
        """,
        tags=['Tender Management'],
        request_body=TenderDocumentUploadSerializer,
        responses={
            201: openapi.Response(
                description="Document attached successfully",
                schema=TenderDocumentSerializer()
            )
        }
    )
    @action(detail=True, methods=['post'], url_path='attach-document')
    def attach_document(self, request, pk=None):
        """Attach a document to a tender"""
        tender = self.get_object()
        serializer = TenderDocumentUploadSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        file = serializer.validated_data['file']
        description = serializer.validated_data.get('description', None)
        
        try:
            document = TenderDocument.objects.create(
                tender=tender,
                file=file,
                created_by=request.user
            )
            
            # Create activity log
            ActivityLog.objects.create(
                entity_type=ActivityLog.EntityType.TENDER,
                entity_id=tender.id,
                action=ActivityLog.Action.UPDATED,
                description=f"Document attached to tender {tender.name}",
                created_by=request.user
            )
            
            document_serializer = TenderDocumentSerializer(document, context={'request': request})
            return Response(document_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Error attaching document: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_id='tender_download_document',
        operation_summary="Download Tender Document",
        operation_description="""
        Download a specific document attached to a tender.
        
        **What it does:**
        - Validates that the document belongs to the specified tender
        - Retrieves the file associated with that document
        - Returns the file as a downloadable attachment
        
        **File Naming:**
        Downloaded file will retain its original filename.
        
        **Use Case:**
        Use this endpoint to download documents attached to a tender for reference.
        
        **Path Parameters:**
        - tender_id: ID of the tender
        - document_id: ID of the document to download
        """,
        tags=['Tender Management'],
        responses={
            200: openapi.Response(
                description="File download",
                schema=openapi.Schema(type=openapi.TYPE_FILE)
            ),
            404: openapi.Response(description="Document not found")
        }
    )
    @action(detail=True, methods=['get'], url_path='download-document/(?P<document_id>[0-9]+)')
    def download_document(self, request, pk=None, document_id=None):
        """Download a tender document"""
        try:
            tender = self.get_object()
            document = TenderDocument.objects.get(
                id=document_id,
                tender_id=pk
            )
            
            if not document.file:
                return Response(
                    {'error': 'File not found for this document'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get file name
            filename = document.file.name.split('/')[-1]
            
            # Create file response
            response = FileResponse(
                document.file.open('rb'),
                as_attachment=True,
                filename=filename
            )
            response['Content-Disposition'] = f'attachment; filename="{quote(filename)}"'
            return response
            
        except TenderDocument.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Error downloading file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_id='tender_activity_feed',
        operation_summary="Get Tender Activity Feed",
        operation_description="""
        Retrieve activity feed for a specific tender showing all activities related to that tender.
        
        **What it returns:**
        - List of all activities related to the tender
        - Activity details include: action, description, timestamp, creator
        - Activities are sorted by creation date (newest first)
        
        **Use Case:**
        Use this endpoint to display activity feed in the tender detail page showing all actions performed on the tender.
        """,
        tags=['Tender Management'],
        responses={
            200: openapi.Response(
                description="Activity feed for the tender",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'activities': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT),
                            description='List of activities'
                        )
                    }
                )
            )
        }
    )
    @action(detail=True, methods=['get'], url_path='activity-feed')
    def activity_feed(self, request, pk=None):
        """Get activity feed for a tender"""
        tender = self.get_object()
        
        activities = ActivityLog.objects.filter(
            entity_type=ActivityLog.EntityType.TENDER,
            entity_id=tender.id
        ).select_related('created_by').order_by('-created_at')
        
        serializer = ActivityFeedSerializer(activities, many=True, context={'request': request})
        return Response({'activities': serializer.data}, status=status.HTTP_200_OK)
