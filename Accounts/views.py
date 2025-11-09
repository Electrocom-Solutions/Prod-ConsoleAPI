"""
Views for Accounts app - Payment Tracking Module.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.db import transaction
from datetime import date
from calendar import monthrange
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import pandas as pd
import logging

from .models import PaymentTracker
from .serializers import (
    PaymentTrackerListSerializer,
    PaymentTrackerDetailSerializer,
    PaymentTrackerUploadSerializer,
    PaymentTrackerMarkPaidSerializer,
    BulkMarkPaymentPaidSerializer,
    PaymentTrackerStatisticsSerializer
)

logger = logging.getLogger(__name__)


class PaymentTrackerViewSet(viewsets.ModelViewSet):
    """
    Payment Tracking APIs
    """
    queryset = PaymentTracker.objects.select_related('created_by', 'updated_by').all()
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return PaymentTrackerListSerializer
        elif self.action in ['retrieve']:
            return PaymentTrackerDetailSerializer
        elif self.action in ['upload']:
            return PaymentTrackerUploadSerializer
        elif self.action in ['mark_paid']:
            return PaymentTrackerMarkPaidSerializer
        elif self.action in ['bulk_mark_paid']:
            return BulkMarkPaymentPaidSerializer
        return PaymentTrackerListSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search by worker name, mobile number, or place of work
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(worker_name__icontains=search) |
                Q(mobile_number__icontains=search) |
                Q(place_of_work__icontains=search)
            )
        
        # Filter by month and year (default to current month and year)
        month_filter = self.request.query_params.get('month', None)
        year_filter = self.request.query_params.get('year', None)
        
        if month_filter and year_filter:
            # Filter by specific month and year
            month = int(month_filter)
            year = int(year_filter)
            # Get first day of the month
            first_day = date(year, month, 1)
            queryset = queryset.filter(sheet_period=first_day)
        else:
            # Default to current month and year if no month/year filters are provided
            today = date.today()
            first_day = date(today.year, today.month, 1)
            queryset = queryset.filter(sheet_period=first_day)
        
        return queryset.order_by('-created_at')
    
    @swagger_auto_schema(
        operation_id='payment_tracker_statistics',
        operation_summary="Get Payment Tracking Statistics",
        operation_description="""
        Retrieve statistics for the payment tracking dashboard.
        
        **What it returns:**
        - total_payable: Total payable amount (sum of all net_salary) for the selected month/year
        - pending_payment_count: Number of payment records with status "Pending" in the selected month/year
        - pending_payment_amount: Total amount of pending payments (sum of net_salary for pending records)
        - total_paid: Total amount of paid payments (sum of net_salary for paid records)
        
        **Month/Year Filtering:**
        The statistics can be filtered by month and year using query parameters.
        - If month and year are provided, statistics are calculated for that specific month/year
        - If not provided, statistics default to current month and year
        
        **Query Parameters:**
        - month (optional): Filter by month (1-12)
        - year (optional): Filter by year (YYYY)
        
        **Use Case:**
        Use this endpoint to populate dashboard tiles showing key metrics for payment tracking.
        """,
        tags=['Payment Tracking'],
        manual_parameters=[
            openapi.Parameter(
                'month',
                openapi.IN_QUERY,
                description='Filter by month (1-12), must be used with year',
                type=openapi.TYPE_INTEGER,
                enum=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                required=False
            ),
            openapi.Parameter(
                'year',
                openapi.IN_QUERY,
                description='Filter by year (YYYY), must be used with month',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="Payment tracking statistics",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'total_payable': openapi.Schema(type=openapi.TYPE_NUMBER, description='Total payable amount'),
                        'pending_payment_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of pending payment records'),
                        'pending_payment_amount': openapi.Schema(type=openapi.TYPE_NUMBER, description='Total amount of pending payments'),
                        'total_paid': openapi.Schema(type=openapi.TYPE_NUMBER, description='Total amount of paid payments')
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """Get payment tracking statistics for dashboard"""
        # Get month and year filters (default to current month/year)
        month_filter = request.query_params.get('month', None)
        year_filter = request.query_params.get('year', None)
        
        if month_filter and year_filter:
            month = int(month_filter)
            year = int(year_filter)
            first_day = date(year, month, 1)
        else:
            today = date.today()
            month = today.month
            year = today.year
            first_day = date(year, month, 1)
        
        # Filter payment records by month and year
        payment_queryset = PaymentTracker.objects.filter(sheet_period=first_day)
        
        # Total payable (sum of all net_salary)
        total_payable = payment_queryset.aggregate(
            total=Coalesce(Sum('net_salary'), 0)
        )['total'] or 0
        
        # Pending payment count
        pending_payment_count = payment_queryset.filter(
            payment_status=PaymentTracker.PaymentStatus.PENDING
        ).count()
        
        # Pending payment amount
        pending_payment_amount = payment_queryset.filter(
            payment_status=PaymentTracker.PaymentStatus.PENDING
        ).aggregate(
            total=Coalesce(Sum('net_salary'), 0)
        )['total'] or 0
        
        # Total paid
        total_paid = payment_queryset.filter(
            payment_status=PaymentTracker.PaymentStatus.PAID
        ).aggregate(
            total=Coalesce(Sum('net_salary'), 0)
        )['total'] or 0
        
        data = {
            'total_payable': float(total_payable),
            'pending_payment_count': pending_payment_count,
            'pending_payment_amount': float(pending_payment_amount),
            'total_paid': float(total_paid)
        }
        
        serializer = PaymentTrackerStatisticsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_id='payment_tracker_list',
        operation_summary="List All Payment Tracker Records",
        operation_description="""
        Retrieve a list of all payment tracker records with filtering and search options.
        
        **What it returns:**
        - List of payment tracker records with basic information
        - Worker name, mobile number, place of work, net salary
        - Bank details, payment status, payment date and mode
        
        **Search Options:**
        - search: Search by worker name, mobile number, or place of work (case-insensitive partial match)
        
        **Filtering Options:**
        - month: Filter by month (1-12) - must be used with year
        - year: Filter by year (YYYY) - must be used with month
        
        **Default Behavior:**
        - If no month/year filters are provided, results default to current month and year
        
        **Query Parameters:**
        - search (optional): Search by worker name, mobile number, or place of work
        - month (optional): Filter by month (1-12), must be used with year. Defaults to current month if not provided.
        - year (optional): Filter by year (YYYY), must be used with month. Defaults to current year if not provided.
        
        **Pagination:**
        Results are paginated (20 items per page by default) and sorted by creation date (newest first).
        """,
        tags=['Payment Tracking'],
        manual_parameters=[
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description='Search by worker name, mobile number, or place of work',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'month',
                openapi.IN_QUERY,
                description='Filter by month (1-12), must be used with year. Defaults to current month if not provided.',
                type=openapi.TYPE_INTEGER,
                enum=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                required=False
            ),
            openapi.Parameter(
                'year',
                openapi.IN_QUERY,
                description='Filter by year (YYYY), must be used with month. Defaults to current year if not provided.',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of payment tracker records",
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
        """List all payment tracker records with filtering and search"""
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='payment_tracker_retrieve',
        operation_summary="Get Payment Tracker Record Details",
        operation_description="""
        Retrieve detailed information about a specific payment tracker record.
        
        **What it returns:**
        - Complete payment tracker record information including all details
        - Sheet attachment URL if available
        """,
        tags=['Payment Tracking'],
        responses={
            200: PaymentTrackerDetailSerializer()
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """Get payment tracker record details"""
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='payment_tracker_upload',
        operation_summary="Upload Excel Sheet with Payment Data",
        operation_description="""
        Upload an Excel sheet containing payment information for a specific month and year.
        
        **What it does:**
        - Accepts an Excel file with payment data
        - Processes the Excel file and creates payment tracker records
        - If records for the same month/year already exist, they are replaced with new data
        - Default payment status is set to "Pending"
        
        **Required Fields:**
        - month: Month (1-12)
        - year: Year (YYYY)
        - excel_file: Excel file with payment information
        
        **Excel File Format:**
        The Excel file must contain the following columns:
        - Sr. No.
        - Worker Name
        - Place Of Work
        - Mobile Number
        - Net Salary
        - Bank Name
        - Account Number
        - IFSC Code
        
        **Important Notes:**
        - If payment tracker records for the same month and year already exist, they will be replaced with the new data
        - All records are created with payment_status="Pending" by default
        - The Excel file is saved as sheet_attachment for reference
        
        **Response:**
        Returns the number of records created/updated and any errors encountered.
        """,
        tags=['Payment Tracking'],
        request_body=PaymentTrackerUploadSerializer,
        responses={
            200: openapi.Response(
                description="Excel file processed successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message'),
                        'records_created': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of records created'),
                        'records_replaced': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of records replaced'),
                        'errors': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING),
                            description='List of errors encountered'
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid request data or Excel file format",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request):
        """Upload Excel sheet with payment data"""
        serializer = PaymentTrackerUploadSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        month = serializer.validated_data['month']
        year = serializer.validated_data['year']
        excel_file = serializer.validated_data['excel_file']
        
        # Validate month and year
        if month < 1 or month > 12:
            return Response(
                {'error': 'Invalid month. Must be between 1 and 12.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate sheet_period (first day of the month)
        try:
            sheet_period = date(year, month, 1)
        except ValueError as e:
            return Response(
                {'error': f'Invalid date: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Read Excel file
            df = pd.read_excel(excel_file)
            
            # Validate required columns
            required_columns = ['Sr. No.', 'Worker Name', 'Place Of Work', 'Mobile Number', 
                              'Net Salary', 'Bank Name', 'Account Number', 'IFSC Code']
            
            # Normalize column names (remove spaces, convert to lowercase)
            df.columns = df.columns.str.strip()
            
            # Check if all required columns exist
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return Response(
                    {'error': f'Missing required columns: {", ".join(missing_columns)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            records_created = 0
            records_replaced = 0
            errors = []
            
            with transaction.atomic():
                # Delete existing records for this month/year
                existing_count = PaymentTracker.objects.filter(sheet_period=sheet_period).count()
                if existing_count > 0:
                    PaymentTracker.objects.filter(sheet_period=sheet_period).delete()
                    records_replaced = existing_count
                
                # Process each row in the Excel file
                for index, row in df.iterrows():
                    try:
                        # Extract data from row
                        worker_name = str(row['Worker Name']).strip() if pd.notna(row['Worker Name']) else ''
                        place_of_work = str(row['Place Of Work']).strip() if pd.notna(row['Place Of Work']) else ''
                        mobile_number = str(row['Mobile Number']).strip() if pd.notna(row['Mobile Number']) else ''
                        net_salary = row['Net Salary']
                        bank_name = str(row['Bank Name']).strip() if pd.notna(row['Bank Name']) else None
                        account_number = str(row['Account Number']).strip() if pd.notna(row['Account Number']) else None
                        ifsc_code = str(row['IFSC Code']).strip() if pd.notna(row['IFSC Code']) else None
                        
                        # Validate required fields
                        if not worker_name:
                            errors.append(f"Row {index + 2}: Worker Name is required")
                            continue
                        
                        if not mobile_number:
                            errors.append(f"Row {index + 2}: Mobile Number is required")
                            continue
                        
                        if pd.isna(net_salary):
                            errors.append(f"Row {index + 2}: Net Salary is required")
                            continue
                        
                        # Convert net_salary to Decimal
                        try:
                            net_salary = float(net_salary)
                        except (ValueError, TypeError):
                            errors.append(f"Row {index + 2}: Invalid Net Salary value")
                            continue
                        
                        # Create payment tracker record
                        PaymentTracker.objects.create(
                            worker_name=worker_name,
                            mobile_number=mobile_number,
                            place_of_work=place_of_work,
                            net_salary=net_salary,
                            bank_name=bank_name,
                            account_number=account_number,
                            ifsc_code=ifsc_code,
                            sheet_period=sheet_period,
                            sheet_attachment=excel_file,
                            payment_status=PaymentTracker.PaymentStatus.PENDING,
                            created_by=request.user
                        )
                        
                        records_created += 1
                        
                    except Exception as e:
                        errors.append(f"Row {index + 2}: {str(e)}")
                        logger.error(f"Error processing row {index + 2}: {str(e)}")
                        continue
            
            return Response({
                'message': 'Excel file processed successfully',
                'records_created': records_created,
                'records_replaced': records_replaced,
                'errors': errors if errors else None
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error processing Excel file: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Error processing Excel file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_id='payment_tracker_mark_paid',
        operation_summary="Mark Payment Tracker Record as Paid",
        operation_description="""
        Mark a single payment tracker record as paid by updating payment details.
        
        **What it does:**
        - Updates the payment tracker record's status to "Paid"
        - Sets payment_date and payment_mode
        - Returns the updated payment tracker record
        
        **Required Fields:**
        - payment_date: Payment date (YYYY-MM-DD)
        - payment_mode: Payment mode (Cash, Cheque, Bank Transfer, UPI)
        
        **Response:**
        Returns the updated payment tracker record with payment details.
        """,
        tags=['Payment Tracking'],
        request_body=PaymentTrackerMarkPaidSerializer,
        responses={
            200: openapi.Response(
                description="Payment tracker record marked as paid successfully",
                schema=PaymentTrackerDetailSerializer()
            ),
            404: openapi.Response(description="Payment tracker record not found")
        }
    )
    @action(detail=True, methods=['post'], url_path='mark-paid')
    def mark_paid(self, request, pk=None):
        """Mark a payment tracker record as paid"""
        payment = self.get_object()
        serializer = PaymentTrackerMarkPaidSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                payment.payment_status = PaymentTracker.PaymentStatus.PAID
                payment.payment_date = serializer.validated_data['payment_date']
                payment.payment_mode = serializer.validated_data['payment_mode']
                payment.updated_by = request.user
                payment.save()
            
            detail_serializer = PaymentTrackerDetailSerializer(payment, context={'request': request})
            return Response(detail_serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error marking payment as paid: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Error marking payment as paid: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_id='payment_tracker_bulk_mark_paid',
        operation_summary="Bulk Mark Payment Tracker Records as Paid",
        operation_description="""
        Mark multiple payment tracker records as paid in bulk. All selected records will be updated with the same payment details.
        
        **What it does:**
        - Accepts a list of payment tracker record IDs
        - Updates all selected records' status to "Paid"
        - Sets the same payment_date and payment_mode for all records
        - Returns the number of records updated and any errors
        
        **Request Body:**
        ```json
        {
          "payment_ids": [1, 2, 3, 4, 5],
          "payment_date": "2024-12-15",
          "payment_mode": "Bank Transfer"
        }
        ```
        
        **Required Fields:**
        - payment_ids: List of payment tracker record IDs to mark as paid
        - payment_date: Payment date (YYYY-MM-DD)
        - payment_mode: Payment mode (Cash, Cheque, Bank Transfer, UPI)
        
        **Validation:**
        - At least one payment ID is required
        - Only valid payment IDs will be processed
        - All operations are performed in a database transaction for data consistency
        
        **Response:**
        Returns the number of records updated, skipped count, and any errors encountered.
        
        **Use Case:**
        Use this endpoint when users select multiple payment tracker records and click "Mark as Paid" button to process them all at once with the same payment details.
        """,
        tags=['Payment Tracking'],
        request_body=BulkMarkPaymentPaidSerializer,
        responses={
            200: openapi.Response(
                description="Payment tracker records marked as paid successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'updated_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of records updated'),
                        'skipped_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of records skipped (not found)'),
                        'errors': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING),
                            description='List of errors encountered'
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid request data",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['post'], url_path='bulk-mark-paid')
    def bulk_mark_paid(self, request):
        """Mark multiple payment tracker records as paid"""
        serializer = BulkMarkPaymentPaidSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        payment_ids = serializer.validated_data['payment_ids']
        payment_date = serializer.validated_data['payment_date']
        payment_mode = serializer.validated_data['payment_mode']
        
        if not payment_ids:
            return Response(
                {'error': 'At least one payment ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Get all payment records that exist
                payments = PaymentTracker.objects.filter(id__in=payment_ids)
                
                updated_count = 0
                skipped_count = 0
                errors = []
                
                valid_ids = set(payments.values_list('id', flat=True))
                invalid_ids = set(payment_ids) - valid_ids
                
                if invalid_ids:
                    skipped_count = len(invalid_ids)
                    errors.append(f"Payment records not found: {', '.join(map(str, invalid_ids))}")
                
                # Update all valid payment records
                for payment in payments:
                    try:
                        payment.payment_status = PaymentTracker.PaymentStatus.PAID
                        payment.payment_date = payment_date
                        payment.payment_mode = payment_mode
                        payment.updated_by = request.user
                        payment.save()
                        updated_count += 1
                    except Exception as e:
                        errors.append(f"Error updating payment {payment.id}: {str(e)}")
                
                return Response({
                    'updated_count': updated_count,
                    'skipped_count': skipped_count,
                    'errors': errors if errors else None
                }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error processing bulk mark as paid: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Error processing bulk mark as paid: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
