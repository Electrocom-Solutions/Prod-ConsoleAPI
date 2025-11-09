from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.db import transaction
from datetime import date, datetime
from calendar import monthrange
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import pandas as pd
from django.contrib.auth.models import User
from Profiles.models import Profile
from Accounts.models import BankAccount
from Projects.models import Project

from .models import Employee, Attendance, ContractWorker, PayrollRecord, HolidayCalander
from .serializers import (
    EmployeeListSerializer,
    EmployeeDetailSerializer,
    EmployeeCreateSerializer,
    EmployeeStatisticsSerializer,
    ContractWorkerListSerializer,
    ContractWorkerDetailSerializer,
    ContractWorkerCreateSerializer,
    ContractWorkerStatisticsSerializer,
    BulkUploadContractWorkerSerializer,
    AttendanceListSerializer,
    AttendanceDetailSerializer,
    AttendanceCreateSerializer,
    AttendanceStatisticsSerializer,
    BulkApproveAttendanceSerializer,
    AttendancePunchInSerializer,
    AttendancePunchOutSerializer,
    PayrollListSerializer,
    PayrollDetailSerializer,
    PayrollCreateSerializer,
    PayrollMarkPaidSerializer,
    BulkMarkPayrollPaidSerializer,
    PayrollStatisticsSerializer,
    HolidayCalendarListSerializer,
    HolidayCalendarDetailSerializer,
    HolidayCalendarCreateUpdateSerializer,
    HolidayCalendarStatisticsSerializer
)
from Notifications.utils import send_notification_to_user


class EmployeeViewSet(viewsets.ModelViewSet):
    """
    Employee Management APIs
    """
    queryset = Employee.objects.select_related(
        'profile', 'profile__user', 'created_by', 'updated_by'
    ).prefetch_related('attendance_records').all()
    parser_classes = [MultiPartParser, FormParser]
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return EmployeeListSerializer
        elif self.action in ['retrieve']:
            return EmployeeDetailSerializer
        return EmployeeCreateSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search by employee name
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(profile__user__first_name__icontains=search) |
                Q(profile__user__last_name__icontains=search) |
                Q(profile__user__username__icontains=search) |
                Q(employee_code__icontains=search)
            )
        
        # Filter by designation
        designation_filter = self.request.query_params.get('designation', None)
        if designation_filter:
            queryset = queryset.filter(designation=designation_filter)
        
        # Filter by availability (present/absent)
        availability_filter = self.request.query_params.get('availability', None)
        if availability_filter:
            today = date.today()
            if availability_filter.lower() == 'present':
                # Get employees who have attendance record with status "Present" for today
                present_employee_ids = Attendance.objects.filter(
                    attendance_date=today,
                    attendance_status=Attendance.AttendanceStatus.PRESENT
                ).values_list('employee_id', flat=True)
                queryset = queryset.filter(id__in=present_employee_ids)
            elif availability_filter.lower() == 'absent':
                # Get employees who have attendance record with status "Absent" for today
                absent_employee_ids = Attendance.objects.filter(
                    attendance_date=today,
                    attendance_status=Attendance.AttendanceStatus.ABSENT
                ).values_list('employee_id', flat=True)
                queryset = queryset.filter(id__in=absent_employee_ids)
        
        return queryset.order_by('-created_at')
    
    @swagger_auto_schema(
        operation_id='employee_list',
        operation_summary="List All Employees",
        operation_description="""
        Retrieve a list of all employees with filtering and search options.
        
        **What it returns:**
        - List of employees with basic information (employee code, name, email, phone, designation)
        - Availability status (Present/Absent) for today
        - Created date
        
        **Search Options:**
        - search: Search by employee name (first name, last name, username) or employee code (case-insensitive partial match)
        
        **Filtering Options:**
        - designation: Filter by designation (Technician, Field Staff, Computer Operator, Other)
        - availability: Filter by availability status (present/absent) - based on today's attendance
        
        **Query Parameters:**
        - search (optional): Search by employee name or employee code
        - designation (optional): Filter by designation
        - availability (optional): Filter by availability status (present/absent)
        
        **Pagination:**
        Results are paginated (20 items per page by default) and sorted by creation date (newest first).
        """,
        tags=['Employee Management'],
        manual_parameters=[
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description='Search by employee name or employee code',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'designation',
                openapi.IN_QUERY,
                description='Filter by designation (Technician, Field Staff, Computer Operator, Other)',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'availability',
                openapi.IN_QUERY,
                description='Filter by availability status (present/absent) - based on today\'s attendance',
                type=openapi.TYPE_STRING,
                enum=['present', 'absent'],
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of employees",
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
        """List all employees with filtering and search"""
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='employee_retrieve',
        operation_summary="Get Employee Details",
        operation_description="""
        Retrieve detailed information about a specific employee including all personal and professional details.
        
        **What it returns:**
        - Complete employee information including personal details, contact information, address
        - Professional information (designation, joining date, salary)
        - Photo URL and document URLs (Aadhar card, PAN card)
        - Creation and update timestamps
        """,
        tags=['Employee Management'],
        responses={
            200: EmployeeDetailSerializer()
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """Get employee details"""
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='employee_create',
        operation_summary="Create New Employee",
        operation_description="""
        Create a new employee with all required and optional information.
        
        **Required Fields:**
        - first_name: Employee's first name
        - last_name: Employee's last name
        - email: Employee's email address
        - employee_code: Unique employee code
        - designation: Designation (Technician, Field Staff, Computer Operator, Other)
        - joining_date: Date of joining (YYYY-MM-DD)
        - monthly_salary: Monthly salary amount
        
        **Optional Fields:**
        - phone_number: Employee's phone number
        - photo: Employee's photo (image file)
        - date_of_birth: Date of birth (YYYY-MM-DD)
        - gender: Gender (male/female)
        - address: Full address
        - city: City name
        - state: State name
        - pin_code: PIN/ZIP code
        - country: Country name
        - aadhar_number: Aadhar card number
        - pan_number: PAN card number
        - aadhar_card: Aadhar card document file
        - pan_card: PAN card document file
        
        **Response:**
        Returns the created employee with all details.
        """,
        tags=['Employee Management'],
        responses={
            201: openapi.Response(
                description="Employee created successfully",
                schema=EmployeeCreateSerializer()
            )
        }
    )
    def create(self, request, *args, **kwargs):
        """Create a new employee"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @swagger_auto_schema(
        operation_id='employee_update',
        operation_summary="Update Employee",
        operation_description="""
        Update an existing employee's information. All fields are optional - only provided fields will be updated.
        
        **Fields:**
        Same as create endpoint - all fields are optional for update.
        
        **Response:**
        Returns the updated employee with all details.
        """,
        tags=['Employee Management'],
        responses={
            200: openapi.Response(
                description="Employee updated successfully",
                schema=EmployeeCreateSerializer()
            )
        }
    )
    def update(self, request, *args, **kwargs):
        """Update employee information"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_id='employee_partial_update',
        operation_summary="Partial Update Employee",
        operation_description="""
        Partially update an employee's information. Only provided fields will be updated.
        
        **Use Case:**
        Use this endpoint when you only want to update specific fields without affecting others.
        """,
        tags=['Employee Management'],
        responses={
            200: openapi.Response(
                description="Employee partially updated successfully",
                schema=EmployeeCreateSerializer()
            )
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """Partially update employee information"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='employee_delete',
        operation_summary="Delete Employee",
        operation_description="""
        Delete an employee from the system. This action is permanent and cannot be undone.
        
        **Warning:**
        Deleting an employee will also delete all associated data including:
        - All attendance records
        - All payroll records
        - All tasks assigned to the employee
        - All related records
        
        **Use Case:**
        Use this endpoint when you need to permanently remove an employee from the system.
        """,
        tags=['Employee Management'],
        responses={
            204: openapi.Response(description="Employee deleted successfully"),
            404: openapi.Response(description="Employee not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        """Delete an employee"""
        return super().destroy(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='employee_statistics',
        operation_summary="Get Employee Management Statistics",
        operation_description="""
        Retrieve statistics for the employee management dashboard.
        
        **What it returns:**
        - total_employees: Total number of employees in the system
        - total_present: Number of employees marked as "Present" today
        - total_absent: Number of employees marked as "Absent" today
        - monthly_payroll: Sum of all employees' monthly salaries
        
        **Calculation:**
        - Total Present: Count of employees with attendance record for today with status "Present"
        - Total Absent: Count of employees with attendance record for today with status "Absent"
        - Monthly Payroll: Sum of all employees' monthly_salary field
        
        **Use Case:**
        Use this endpoint to populate dashboard tiles showing key metrics for employee management.
        """,
        tags=['Employee Management'],
        responses={
            200: openapi.Response(
                description="Employee management statistics",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'total_employees': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total number of employees'),
                        'total_present': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of employees present today'),
                        'total_absent': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of employees absent today'),
                        'monthly_payroll': openapi.Schema(type=openapi.TYPE_NUMBER, description='Total monthly payroll (sum of all salaries)')
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """Get employee management statistics for dashboard"""
        today = date.today()
        
        # Total employees
        total_employees = Employee.objects.count()
        
        # Total present today (employees with attendance record marked as Present)
        total_present = Attendance.objects.filter(
            attendance_date=today,
            attendance_status=Attendance.AttendanceStatus.PRESENT
        ).values('employee').distinct().count()
        
        # Total absent today (employees with attendance record marked as Absent)
        total_absent = Attendance.objects.filter(
            attendance_date=today,
            attendance_status=Attendance.AttendanceStatus.ABSENT
        ).values('employee').distinct().count()
        
        # Monthly payroll (sum of all employees' monthly salaries)
        monthly_payroll = Employee.objects.aggregate(
            total=Coalesce(Sum('monthly_salary'), 0)
        )['total'] or 0
        
        data = {
            'total_employees': total_employees,
            'total_present': total_present,
            'total_absent': total_absent,
            'monthly_payroll': float(monthly_payroll)
        }
        
        serializer = EmployeeStatisticsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ContractWorkerViewSet(viewsets.ModelViewSet):
    """
    Contract Worker Management APIs
    """
    queryset = ContractWorker.objects.select_related(
        'profile', 'profile__user', 'project', 'created_by', 'updated_by'
    ).prefetch_related('profile__bank_accounts').all()
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return ContractWorkerListSerializer
        elif self.action in ['retrieve']:
            return ContractWorkerDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ContractWorkerCreateSerializer
        elif self.action in ['bulk_upload']:
            return BulkUploadContractWorkerSerializer
        return ContractWorkerListSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search by worker name
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(profile__user__first_name__icontains=search) |
                Q(profile__user__last_name__icontains=search) |
                Q(profile__user__username__icontains=search)
            )
        
        # Filter by worker_type (designation)
        worker_type_filter = self.request.query_params.get('worker_type', None)
        if worker_type_filter:
            queryset = queryset.filter(worker_type=worker_type_filter)
        
        # Filter by availability (assigned/available)
        availability_filter = self.request.query_params.get('availability', None)
        if availability_filter:
            if availability_filter.lower() == 'assigned':
                # Filter for workers who have a project assigned
                queryset = queryset.filter(project__isnull=False)
            elif availability_filter.lower() == 'available':
                # Filter for workers who don't have a project assigned
                queryset = queryset.filter(project__isnull=True)
        
        return queryset.order_by('-created_at')
    
    @swagger_auto_schema(
        operation_id='contract_worker_statistics',
        operation_summary="Get Contract Worker Management Statistics",
        operation_description="""
        Retrieve statistics for the contract worker management dashboard.
        
        **What it returns:**
        - total_workers: Total number of contract workers in the system
        - total_available: Number of workers not assigned to any project
        - total_assigned: Number of workers assigned to a project today (based on assignment date)
        - total_monthly_payroll: Sum of all contract workers' monthly salaries
        
        **Calculation:**
        - Total Available: Count of workers where project is NULL
        - Total Assigned: Count of workers where project is NOT NULL
        - Total Monthly Payroll: Sum of all workers' monthly_salary field
        
        **Use Case:**
        Use this endpoint to populate dashboard tiles showing key metrics for contract worker management.
        """,
        tags=['Contract Worker Management'],
        responses={
            200: openapi.Response(
                description="Contract worker management statistics",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'total_workers': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total number of contract workers'),
                        'total_available': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of workers not assigned to any project'),
                        'total_assigned': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of workers assigned to a project'),
                        'total_monthly_payroll': openapi.Schema(type=openapi.TYPE_NUMBER, description='Total monthly payroll (sum of all salaries)')
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """Get contract worker management statistics for dashboard"""
        today = date.today()
        
        # Total workers
        total_workers = ContractWorker.objects.count()
        
        # Total available (workers not assigned to any project)
        total_available = ContractWorker.objects.filter(project__isnull=True).count()
        
        # Total assigned (workers assigned to a project)
        total_assigned = ContractWorker.objects.filter(project__isnull=False).count()
        
        # Monthly payroll (sum of all workers' monthly salaries)
        monthly_payroll = ContractWorker.objects.aggregate(
            total=Coalesce(Sum('monthly_salary'), 0)
        )['total'] or 0
        
        data = {
            'total_workers': total_workers,
            'total_available': total_available,
            'total_assigned': total_assigned,
            'total_monthly_payroll': float(monthly_payroll)
        }
        
        serializer = ContractWorkerStatisticsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_id='contract_worker_list',
        operation_summary="List All Contract Workers",
        operation_description="""
        Retrieve a list of all contract workers with filtering and search options.
        
        **What it returns:**
        - List of contract workers with basic information (name, email, phone, worker type, department, monthly salary)
        - Availability status (assigned/available) based on project assignment
        - Project name if assigned
        - Created date
        
        **Search Options:**
        - search: Search by worker name (first name, last name, username) - case-insensitive partial match
        
        **Filtering Options:**
        - worker_type: Filter by worker type (Unskilled, Semi-Skilled, Skilled)
        - availability: Filter by availability status (assigned/available)
          * 'assigned': Workers who have a project assigned
          * 'available': Workers who don't have a project assigned
        
        **Query Parameters:**
        - search (optional): Search by worker name
        - worker_type (optional): Filter by worker type
        - availability (optional): Filter by availability status (assigned/available)
        
        **Pagination:**
        Results are paginated (20 items per page by default) and sorted by creation date (newest first).
        """,
        tags=['Contract Worker Management'],
        manual_parameters=[
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description='Search by worker name (first name, last name, username)',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'worker_type',
                openapi.IN_QUERY,
                description='Filter by worker type (Unskilled, Semi-Skilled, Skilled)',
                type=openapi.TYPE_STRING,
                enum=['Unskilled', 'Semi-Skilled', 'Skilled'],
                required=False
            ),
            openapi.Parameter(
                'availability',
                openapi.IN_QUERY,
                description='Filter by availability status (assigned/available)',
                type=openapi.TYPE_STRING,
                enum=['assigned', 'available'],
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of contract workers",
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
        """List all contract workers with filtering and search"""
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='contract_worker_retrieve',
        operation_summary="Get Contract Worker Details",
        operation_description="""
        Retrieve detailed information about a specific contract worker including all personal and professional details.
        
        **What it returns:**
        - Complete contract worker information including personal details, contact information, address
        - Professional information (worker type, monthly salary, department)
        - Aadhar number and UAN number
        - Project assignment (if any)
        - Bank account details
        - Creation and update timestamps
        """,
        tags=['Contract Worker Management'],
        responses={
            200: ContractWorkerDetailSerializer()
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """Get contract worker details"""
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='contract_worker_create',
        operation_summary="Create New Contract Worker",
        operation_description="""
        Create a new contract worker with all required and optional information.
        
        **Required Fields:**
        - first_name: Worker's first name
        - last_name: Worker's last name
        - email: Worker's email address
        - worker_type: Worker type (Unskilled, Semi-Skilled, Skilled)
        - monthly_salary: Monthly salary amount
        - aadhar_no: Aadhar card number
        
        **Optional Fields:**
        - phone_number: Worker's phone number
        - date_of_birth: Date of birth (YYYY-MM-DD)
        - gender: Gender (male/female)
        - address: Full address
        - city: City name
        - state: State name
        - pin_code: PIN/ZIP code
        - country: Country name
        - uan_number: UAN number
        - department: Department name
        - project: Project ID (if assigning to a project)
        - bank_name: Bank name
        - bank_account_number: Bank account number
        - ifsc_code: IFSC code
        - bank_branch: Bank branch name
        
        **Response:**
        Returns the created contract worker with all details.
        """,
        tags=['Contract Worker Management'],
        responses={
            201: openapi.Response(
                description="Contract worker created successfully",
                schema=ContractWorkerCreateSerializer()
            )
        }
    )
    def create(self, request, *args, **kwargs):
        """Create a new contract worker"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @swagger_auto_schema(
        operation_id='contract_worker_update',
        operation_summary="Update Contract Worker",
        operation_description="""
        Update an existing contract worker's information. All fields are optional - only provided fields will be updated.
        
        **Fields:**
        Same as create endpoint - all fields are optional for update.
        
        **Response:**
        Returns the updated contract worker with all details.
        """,
        tags=['Contract Worker Management'],
        responses={
            200: openapi.Response(
                description="Contract worker updated successfully",
                schema=ContractWorkerCreateSerializer()
            )
        }
    )
    def update(self, request, *args, **kwargs):
        """Update contract worker information"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_id='contract_worker_partial_update',
        operation_summary="Partial Update Contract Worker",
        operation_description="""
        Partially update a contract worker's information. Only provided fields will be updated.
        
        **Use Case:**
        Use this endpoint when you only want to update specific fields without affecting others.
        """,
        tags=['Contract Worker Management'],
        responses={
            200: openapi.Response(
                description="Contract worker partially updated successfully",
                schema=ContractWorkerCreateSerializer()
            )
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """Partially update contract worker information"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='contract_worker_delete',
        operation_summary="Delete Contract Worker",
        operation_description="""
        Delete a contract worker from the system. This action is permanent and cannot be undone.
        
        **Warning:**
        Deleting a contract worker will also delete all associated data including:
        - Associated Profile and User records
        - Bank account details
        - All related records
        
        **Use Case:**
        Use this endpoint when you need to permanently remove a contract worker from the system.
        """,
        tags=['Contract Worker Management'],
        responses={
            204: openapi.Response(description="Contract worker deleted successfully"),
            404: openapi.Response(description="Contract worker not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        """Delete a contract worker"""
        return super().destroy(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='contract_worker_bulk_upload',
        operation_summary="Bulk Upload Contract Workers from Excel",
        operation_description="""
        Bulk upload contract workers from an Excel file (.xlsx or .xls).
        
        **Excel File Format:**
        The Excel file must contain the following columns (case-insensitive):
        - Sr. No. (optional, for reference)
        - First Name (required)
        - Last Name (required)
        - Email (required)
        - Phone Number (optional)
        - Date Of Birth (dd/mm/yy format) (optional)
        - Gender (male/female) (optional)
        - Address (optional)
        - City (optional)
        - State (optional)
        - Pincode (optional)
        - Country (optional)
        - Worker Type (unskilled, semiskilled, skilled) (required)
        - Salary (monthly salary) (required)
        - Aadhar Number (required)
        - UAN Number (optional)
        - Department (optional)
        - Bank Name (optional)
        - Account Number (optional)
        - IFSC Code (optional)
        - Bank Branch (optional)
        - Project (optional) - Project name or ID to assign the worker to a project
        
        **What it does:**
        - Reads the Excel file and processes each row
        - Creates User, Profile, BankAccount (if bank details provided), and ContractWorker records
        - Assigns worker to project if project name/ID is provided in the Excel file
        - Returns a summary of successful and failed imports
        
        **Response:**
        Returns the number of workers successfully imported, failed imports, and any errors encountered.
        
        **Example Response:**
        ```json
        {
            "success_count": 50,
            "failed_count": 2,
            "errors": [
                "Row 5: Email is required",
                "Row 12: Invalid worker type"
            ]
        }
        ```
        """,
        tags=['Contract Worker Management'],
        responses={
            200: openapi.Response(
                description="Bulk upload completed",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of workers successfully imported'),
                        'failed_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of workers that failed to import'),
                        'errors': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING),
                            description='List of errors encountered during import'
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid file format or missing file",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['post'], url_path='bulk-upload')
    def bulk_upload(self, request):
        """Bulk upload contract workers from Excel file"""
        serializer = BulkUploadContractWorkerSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        excel_file = serializer.validated_data['excel_file']
        
        # Validate file extension
        if not excel_file.name.endswith(('.xlsx', '.xls')):
            return Response(
                {'error': 'Invalid file format. Please upload an Excel file (.xlsx or .xls)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Read Excel file
            df = pd.read_excel(excel_file)
            
            # Normalize column names (case-insensitive, strip whitespace)
            df.columns = df.columns.str.strip().str.lower()
            
            # Map column names to expected format
            column_mapping = {
                'sr. no.': 'sr_no',
                'sr no': 'sr_no',
                'sr no.': 'sr_no',
                'first name': 'first_name',
                'last name': 'last_name',
                'phone number': 'phone_number',
                'date of birth (dd/mm/yy)': 'date_of_birth',
                'date of birth': 'date_of_birth',
                'dob': 'date_of_birth',
                'gender (male/female)': 'gender',
                'gender': 'gender',
                'worker type (unskilled, semiskilled, skilled)': 'worker_type',
                'worker type': 'worker_type',
                'worker_type': 'worker_type',
                'salary': 'monthly_salary',
                'monthly salary': 'monthly_salary',
                'aadhar number': 'aadhar_no',
                'aadhar no': 'aadhar_no',
                'uan number': 'uan_number',
                'uan': 'uan_number',
                'account number': 'account_number',
                'bank account number': 'account_number',
                'ifsc code': 'ifsc_code',
                'ifsc': 'ifsc_code',
                'bank branch': 'bank_branch',
                'branch': 'bank_branch',
                'project': 'project',
                'project name': 'project',
                'project_id': 'project'
            }
            
            # Rename columns
            df = df.rename(columns=column_mapping)
            
            success_count = 0
            failed_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                row_num = index + 2  # Excel row number (1-indexed, +1 for header)
                
                try:
                    # Extract required fields
                    first_name = str(row.get('first_name', '')).strip()
                    last_name = str(row.get('last_name', '')).strip()
                    email = str(row.get('email', '')).strip()
                    worker_type_str = str(row.get('worker_type', '')).strip()
                    salary_str = str(row.get('monthly_salary', '')).strip()
                    aadhar_no = str(row.get('aadhar_no', '')).strip()
                    
                    # Validate required fields
                    if not first_name:
                        errors.append(f"Row {row_num}: First Name is required")
                        failed_count += 1
                        continue
                    
                    if not last_name:
                        errors.append(f"Row {row_num}: Last Name is required")
                        failed_count += 1
                        continue
                    
                    if not email:
                        errors.append(f"Row {row_num}: Email is required")
                        failed_count += 1
                        continue
                    
                    if not worker_type_str:
                        errors.append(f"Row {row_num}: Worker Type is required")
                        failed_count += 1
                        continue
                    
                    # Map worker type (case-insensitive)
                    worker_type_map = {
                        'unskilled': 'Unskilled',
                        'semiskilled': 'Semi-Skilled',
                        'semi-skilled': 'Semi-Skilled',
                        'skilled': 'Skilled'
                    }
                    worker_type = worker_type_map.get(worker_type_str.lower())
                    if not worker_type:
                        errors.append(f"Row {row_num}: Invalid worker type '{worker_type_str}'. Must be one of: Unskilled, Semi-Skilled, Skilled")
                        failed_count += 1
                        continue
                    
                    if not salary_str:
                        errors.append(f"Row {row_num}: Monthly Salary is required")
                        failed_count += 1
                        continue
                    
                    try:
                        monthly_salary = float(salary_str)
                    except ValueError:
                        errors.append(f"Row {row_num}: Invalid monthly salary '{salary_str}'")
                        failed_count += 1
                        continue
                    
                    if not aadhar_no:
                        errors.append(f"Row {row_num}: Aadhar Number is required")
                        failed_count += 1
                        continue
                    
                    # Extract optional fields
                    phone_number = str(row.get('phone_number', '')).strip() or None
                    
                    # Parse date of birth
                    date_of_birth = None
                    dob_str = str(row.get('date_of_birth', '')).strip()
                    if dob_str:
                        try:
                            # Try parsing dd/mm/yy or dd/mm/yyyy format
                            if '/' in dob_str:
                                parts = dob_str.split('/')
                                if len(parts) == 3:
                                    day, month, year = parts
                                    year = int(year)
                                    if year < 100:
                                        year += 2000 if year < 50 else 1900
                                    date_of_birth = date(year, int(month), int(day))
                            else:
                                # Try parsing as standard date format
                                date_of_birth = pd.to_datetime(dob_str).date()
                        except:
                            errors.append(f"Row {row_num}: Invalid date format for Date of Birth '{dob_str}'")
                    
                    # Extract gender
                    gender = str(row.get('gender', '')).strip() or None
                    if gender:
                        gender_lower = gender.lower()
                        if gender_lower in ['male', 'm']:
                            gender = 'male'
                        elif gender_lower in ['female', 'f']:
                            gender = 'female'
                        else:
                            gender = None
                    
                    # Extract address fields
                    address = str(row.get('address', '')).strip() or None
                    city = str(row.get('city', '')).strip() or None
                    state = str(row.get('state', '')).strip() or None
                    pin_code = str(row.get('pincode', '')).strip() or str(row.get('pin_code', '')).strip() or None
                    country = str(row.get('country', '')).strip() or None
                    
                    # Extract worker-specific fields
                    uan_number = str(row.get('uan_number', '')).strip() or None
                    department = str(row.get('department', '')).strip() or None
                    
                    # Extract project (by project name or ID)
                    project = None
                    project_str = str(row.get('project', '')).strip()
                    if project_str:
                        try:
                            # Try to find project by name first
                            project = Project.objects.filter(name__icontains=project_str).first()
                            if not project:
                                # Try by ID
                                try:
                                    project_id = int(project_str)
                                    project = Project.objects.filter(id=project_id).first()
                                except ValueError:
                                    pass
                            # Note: If project not found, worker will be created without project assignment
                            # This is not a fatal error, so we don't add to errors list
                        except Exception as e:
                            # Only log error if it's a critical issue
                            pass  # Project assignment is optional, so we continue even if project is not found
                    
                    # Extract bank details
                    bank_name = str(row.get('bank_name', '')).strip() or None
                    account_number = str(row.get('account_number', '')).strip() or None
                    ifsc_code = str(row.get('ifsc_code', '')).strip() or None
                    bank_branch = str(row.get('bank_branch', '')).strip() or None
                    
                    # Create contract worker
                    with transaction.atomic():
                        # Create user
                        username = email or f"contract_worker_{ContractWorker.objects.count() + 1}"
                        base_username = username
                        counter = 1
                        while User.objects.filter(username=username).exists():
                            username = f"{base_username}_{counter}"
                            counter += 1
                        
                        user = User.objects.create_user(
                            username=username,
                            email=email,
                            first_name=first_name,
                            last_name=last_name
                        )
                        
                        # Create profile
                        profile = Profile.objects.create(
                            user=user,
                            date_of_birth=date_of_birth,
                            gender=gender,
                            address=address,
                            city=city,
                            state=state,
                            pin_code=pin_code,
                            country=country,
                            created_by=request.user
                        )
                        
                        # Create bank account if bank details provided
                        if bank_name and account_number and ifsc_code:
                            BankAccount.objects.create(
                                profile=profile,
                                bank_name=bank_name,
                                account_number=account_number,
                                ifsc_code=ifsc_code,
                                branch=bank_branch,
                                created_by=request.user
                            )
                        
                        # Create contract worker
                        ContractWorker.objects.create(
                            profile=profile,
                            project=project,
                            worker_type=worker_type,
                            monthly_salary=monthly_salary,
                            aadhar_no=aadhar_no,
                            uan_number=uan_number,
                            department=department,
                            created_by=request.user
                        )
                        
                        success_count += 1
                
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Row {row_num}: {str(e)}")
                    continue
            
            return Response({
                'success_count': success_count,
                'failed_count': failed_count,
                'errors': errors if errors else None
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {'error': f'Error processing Excel file: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class AttendanceViewSet(viewsets.ModelViewSet):
    """
    Attendance Management APIs
    """
    queryset = Attendance.objects.select_related(
        'employee', 'employee__profile', 'employee__profile__user',
        'created_by', 'updated_by'
    ).all()
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return AttendanceListSerializer
        elif self.action in ['retrieve']:
            return AttendanceDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return AttendanceCreateSerializer
        return AttendanceListSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search by employee name
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(employee__profile__user__first_name__icontains=search) |
                Q(employee__profile__user__last_name__icontains=search) |
                Q(employee__profile__user__username__icontains=search) |
                Q(employee__employee_code__icontains=search)
            )
        
        # Filter by employee ID
        employee_filter = self.request.query_params.get('employee', None)
        if employee_filter:
            queryset = queryset.filter(employee_id=employee_filter)
        
        # Filter by date (brings all attendance for that particular date)
        date_filter = self.request.query_params.get('date', None)
        if date_filter:
            queryset = queryset.filter(attendance_date=date_filter)
        
        # Filter by month and year (default to current month and year)
        month_filter = self.request.query_params.get('month', None)
        year_filter = self.request.query_params.get('year', None)
        
        if month_filter and year_filter:
            # Filter by specific month and year
            month = int(month_filter)
            year = int(year_filter)
            # Get first and last day of the month
            first_day = date(year, month, 1)
            last_day = date(year, month, monthrange(year, month)[1])
            queryset = queryset.filter(
                attendance_date__gte=first_day,
                attendance_date__lte=last_day
            )
        elif not date_filter:
            # Default to current month and year if no date filter is provided
            today = date.today()
            first_day = date(today.year, today.month, 1)
            last_day = date(today.year, today.month, monthrange(today.year, today.month)[1])
            queryset = queryset.filter(
                attendance_date__gte=first_day,
                attendance_date__lte=last_day
            )
        
        # Filter by date range (if date_from and date_to are provided)
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)
        if date_from:
            queryset = queryset.filter(attendance_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(attendance_date__lte=date_to)
        
        # Filter by attendance status
        status_filter = self.request.query_params.get('attendance_status', None)
        if status_filter:
            queryset = queryset.filter(attendance_status=status_filter)
        
        # Filter by approval status
        approval_filter = self.request.query_params.get('approval_status', None)
        if approval_filter:
            queryset = queryset.filter(approval_status=approval_filter)
        
        return queryset.order_by('-attendance_date', '-created_at')
    
    @swagger_auto_schema(
        operation_id='attendance_statistics',
        operation_summary="Get Attendance Dashboard Statistics",
        operation_description="""
        Retrieve statistics for the attendance management dashboard.
        
        **What it returns:**
        - total_working_days: Total working days (default: 26)
        - total_employees_present: Number of employees marked as "Present" today
        - total_employees_absent: Number of employees marked as "Absent" today
        - total_pending_approvals: Number of attendance records with "Pending" approval status
        
        **Calculation:**
        - Total Working Days: Default value is 26 (can be configured)
        - Total Employees Present: Count of employees with attendance record for today with status "Present"
        - Total Employees Absent: Count of employees with attendance record for today with status "Absent"
        - Total Pending Approvals: Count of all attendance records with approval_status "Pending"
        
        **Use Case:**
        Use this endpoint to populate dashboard tiles showing key metrics for attendance management.
        """,
        tags=['Attendance Management'],
        responses={
            200: openapi.Response(
                description="Attendance management statistics",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'total_working_days': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total working days (default: 26)'),
                        'total_employees_present': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of employees present today'),
                        'total_employees_absent': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of employees absent today'),
                        'total_pending_approvals': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of attendance records pending approval')
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """Get attendance management statistics for dashboard"""
        today = date.today()
        
        # Total working days (default: 26)
        total_working_days = 26
        
        # Total employees present today
        total_employees_present = Attendance.objects.filter(
            attendance_date=today,
            attendance_status=Attendance.AttendanceStatus.PRESENT
        ).values('employee').distinct().count()
        
        # Total employees absent today
        total_employees_absent = Attendance.objects.filter(
            attendance_date=today,
            attendance_status=Attendance.AttendanceStatus.ABSENT
        ).values('employee').distinct().count()
        
        # Total pending approvals
        total_pending_approvals = Attendance.objects.filter(
            approval_status=Attendance.ApprovalStatus.PENDING
        ).count()
        
        data = {
            'total_working_days': total_working_days,
            'total_employees_present': total_employees_present,
            'total_employees_absent': total_employees_absent,
            'total_pending_approvals': total_pending_approvals
        }
        
        serializer = AttendanceStatisticsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_id='attendance_list',
        operation_summary="List All Attendance Records",
        operation_description="""
        Retrieve a list of all attendance records with filtering and search options.
        
        **What it returns:**
        - List of attendance records with basic information (employee, date, status, check-in/out times)
        - Employee name and code for easy reference
        - Approval status
        - Notes
        
        **Search Options:**
        - search: Search by employee name (first name, last name, username) or employee code (case-insensitive partial match)
        
        **Filtering Options:**
        - employee: Filter by employee ID
        - date: Filter by specific date (YYYY-MM-DD) - brings all attendance for that particular date
        - month: Filter by month (1-12) - used with year filter
        - year: Filter by year (YYYY) - used with month filter
        - attendance_status: Filter by attendance status (Present, Absent, Half-Day, Leave)
        - approval_status: Filter by approval status (Approved, Pending, Rejected)
        - date_from: Filter by date range start (YYYY-MM-DD)
        - date_to: Filter by date range end (YYYY-MM-DD)
        
        **Default Behavior:**
        - If no date, month, or year filters are provided, results are filtered by default to current month and year
        
        **Query Parameters:**
        - search (optional): Search by employee name or employee code
        - employee (optional): Filter by employee ID
        - date (optional): Filter by specific date (YYYY-MM-DD)
        - month (optional): Filter by month (1-12), must be used with year
        - year (optional): Filter by year (YYYY), must be used with month
        - attendance_status (optional): Filter by attendance status (Present, Absent, Half-Day, Leave)
        - approval_status (optional): Filter by approval status (Approved, Pending, Rejected)
        - date_from (optional): Filter by date range start (YYYY-MM-DD)
        - date_to (optional): Filter by date range end (YYYY-MM-DD)
        
        **Pagination:**
        Results are paginated (20 items per page by default) and sorted by attendance date (newest first).
        """,
        tags=['Attendance Management'],
        manual_parameters=[
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description='Search by employee name (first name, last name, username) or employee code',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'employee',
                openapi.IN_QUERY,
                description='Filter by employee ID',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description='Filter by specific date (YYYY-MM-DD) - brings all attendance for that particular date',
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE,
                required=False
            ),
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
            openapi.Parameter(
                'attendance_status',
                openapi.IN_QUERY,
                description='Filter by attendance status',
                type=openapi.TYPE_STRING,
                enum=['Present', 'Absent', 'Half-Day', 'Leave'],
                required=False
            ),
            openapi.Parameter(
                'approval_status',
                openapi.IN_QUERY,
                description='Filter by approval status',
                type=openapi.TYPE_STRING,
                enum=['Approved', 'Pending', 'Rejected'],
                required=False
            ),
            openapi.Parameter(
                'date_from',
                openapi.IN_QUERY,
                description='Filter by date range start (YYYY-MM-DD)',
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE,
                required=False
            ),
            openapi.Parameter(
                'date_to',
                openapi.IN_QUERY,
                description='Filter by date range end (YYYY-MM-DD)',
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of attendance records",
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
        """List all attendance records with filtering"""
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='attendance_retrieve',
        operation_summary="Get Attendance Record Details",
        operation_description="""
        Retrieve detailed information about a specific attendance record.
        
        **What it returns:**
        - Complete attendance record information including all check-in/out details
        - Employee information
        - Location coordinates if available
        - Notes and approval status
        """,
        tags=['Attendance Management'],
        responses={
            200: AttendanceDetailSerializer()
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """Get attendance record details"""
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='attendance_create',
        operation_summary="Create Attendance Record",
        operation_description="""
        Create or update an attendance record. If a record for the same employee and date already exists, it will be updated with the new data.
        
        **Required Fields:**
        - employee: ID of the employee
        - attendance_date: Date of attendance (YYYY-MM-DD)
        - attendance_status: Attendance status (Present, Absent, Half-Day)
        
        **Optional Fields:**
        - check_in_time: Check-in time (YYYY-MM-DD HH:MM:SS format)
        - check_out_time: Check-out time (YYYY-MM-DD HH:MM:SS format)
        - notes: Additional notes about the attendance
        
        **Important Notes:**
        - If an attendance record for the same employee and date already exists, it will be replaced with the new data
        - The approval_status will be reset to "Pending" when attendance is updated
        - Returns 201 if a new record is created, 200 if an existing record is updated
        
        **Response:**
        Returns the created or updated attendance record.
        """,
        tags=['Attendance Management'],
        responses={
            200: openapi.Response(
                description="Attendance record updated successfully",
                schema=AttendanceCreateSerializer()
            ),
            201: openapi.Response(
                description="Attendance record created successfully",
                schema=AttendanceCreateSerializer()
            )
        }
    )
    def create(self, request, *args, **kwargs):
        """Create or update an attendance record"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attendance = serializer.save()
        
        # Return appropriate status code based on was_created flag
        was_created = getattr(attendance, '_was_created', False)
        if was_created:
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_id='attendance_update',
        operation_summary="Update Attendance Record",
        operation_description="""
        Update an existing attendance record. All fields are optional - only provided fields will be updated.
        
        **Fields:**
        Same as create endpoint - all fields are optional for update.
        
        **Response:**
        Returns the updated attendance record.
        """,
        tags=['Attendance Management'],
        responses={
            200: openapi.Response(
                description="Attendance record updated successfully",
                schema=AttendanceCreateSerializer()
            )
        }
    )
    def update(self, request, *args, **kwargs):
        """Update attendance record information"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_id='attendance_partial_update',
        operation_summary="Partial Update Attendance Record",
        operation_description="""
        Partially update an attendance record. Only provided fields will be updated.
        
        **Use Case:**
        Use this endpoint when you only want to update specific fields without affecting others.
        """,
        tags=['Attendance Management'],
        responses={
            200: openapi.Response(
                description="Attendance record partially updated successfully",
                schema=AttendanceCreateSerializer()
            )
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """Partially update attendance record information"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='attendance_delete',
        operation_summary="Delete Attendance Record",
        operation_description="""
        Delete an attendance record from the system. This action is permanent and cannot be undone.
        
        **Use Case:**
        Use this endpoint when you need to permanently remove an attendance record from the system.
        """,
        tags=['Attendance Management'],
        responses={
            204: openapi.Response(description="Attendance record deleted successfully"),
            404: openapi.Response(description="Attendance record not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        """Delete an attendance record"""
        return super().destroy(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='attendance_bulk_approve',
        operation_summary="Bulk Approve/Reject Attendance Records",
        operation_description="""
        Mark multiple attendance records as approved or rejected in bulk.
        
        **What it does:**
        - Accepts a list of attendance record IDs
        - Updates all selected records' approval_status to "Approved" or "Rejected"
        - Automatically sets attendance_status to "Present" when approved
        - Automatically sets attendance_status to "Absent" when rejected
        - If approval_status is "Rejected", rejection_reason is required
        - Returns the number of records updated and any errors
        
        **Request Body:**
        ```json
        {
          "attendance_ids": [1, 2, 3, 4, 5],
          "approval_status": "Approved",
          "rejection_reason": null  // Only required if approval_status is "Rejected"
        }
        ```
        
        **Validation:**
        - At least one attendance ID is required
        - If approval_status is "Rejected", rejection_reason is required
        - Only valid attendance IDs will be processed
        - All operations are performed in a database transaction for data consistency
        
        **Response:**
        Returns the number of records approved/rejected, skipped count, and any errors encountered.
        
        **Use Case:**
        Use this endpoint when users select multiple attendance records and click "Approve" or "Reject" button to process them all at once.
        """,
        tags=['Attendance Management'],
        responses={
            200: openapi.Response(
                description="Attendance records updated successfully",
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
    @action(detail=False, methods=['post'], url_path='bulk-approve')
    def bulk_approve(self, request):
        """Mark multiple attendance records as approved or rejected"""
        serializer = BulkApproveAttendanceSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        attendance_ids = serializer.validated_data['attendance_ids']
        approval_status = serializer.validated_data['approval_status']
        rejection_reason = serializer.validated_data.get('rejection_reason', None)
        
        if not attendance_ids:
            return Response(
                {'error': 'At least one attendance ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Get all attendance records that exist
                attendances = Attendance.objects.filter(id__in=attendance_ids)
                
                updated_count = 0
                skipped_count = 0
                errors = []
                
                valid_ids = set(attendances.values_list('id', flat=True))
                invalid_ids = set(attendance_ids) - valid_ids
                
                if invalid_ids:
                    skipped_count = len(invalid_ids)
                    errors.append(f"Attendance records not found: {', '.join(map(str, invalid_ids))}")
                
                # Update all valid attendance records
                for attendance in attendances:
                    try:
                        attendance.approval_status = approval_status
                        if approval_status == Attendance.ApprovalStatus.REJECTED:
                            attendance.rejection_reason = rejection_reason
                            # Automatically set attendance_status to "Absent" when rejected
                            attendance.attendance_status = Attendance.AttendanceStatus.ABSENT
                        else:
                            attendance.rejection_reason = None
                            # Automatically set attendance_status to "Present" when approved
                            if approval_status == Attendance.ApprovalStatus.APPROVED:
                                attendance.attendance_status = Attendance.AttendanceStatus.PRESENT
                        attendance.updated_by = request.user
                        attendance.save()
                        
                        # Notify employee when attendance is approved
                        if approval_status == Attendance.ApprovalStatus.APPROVED:
                            if attendance.employee and attendance.employee.profile and attendance.employee.profile.user:
                                employee_user = attendance.employee.profile.user
                                send_notification_to_user(
                                    user=employee_user,
                                    title="Attendance Approved",
                                    message=f"Your attendance for {attendance.attendance_date.strftime('%d %b %Y')} has been approved",
                                    notification_type="System",
                                    created_by=request.user
                                )
                        
                        updated_count += 1
                    except Exception as e:
                        errors.append(f"Error updating attendance {attendance.id}: {str(e)}")
                
                return Response({
                    'updated_count': updated_count,
                    'skipped_count': skipped_count,
                    'errors': errors if errors else None
                }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {'error': f'Error processing bulk approval: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_id='attendance_punch_in',
        operation_summary="Punch In Attendance (Mobile App)",
        operation_description="""
        Punch in attendance from mobile app. This endpoint is designed for employees to mark their attendance using their mobile device.
        
        **What it does:**
        - Accepts selfie image, date, time, location, latitude, and longitude
        - Automatically identifies the employee from the authenticated user
        - Creates or updates attendance record with check-in information
        - Sets attendance_status to "Present" and approval_status to "Pending"
        
        **Required Fields:**
        - selfie: Selfie image file captured during punch-in
        - date: Date of attendance (YYYY-MM-DD)
        - time: Check-in time (YYYY-MM-DD HH:MM:SS format) - must match the date
        - location: Location name or address (string)
        - latitude: Latitude coordinate (decimal)
        - longitude: Longitude coordinate (decimal)
        
        **Important Notes:**
        - The employee is automatically identified from the authenticated user's profile
        - If an attendance record for the same employee and date already exists, it will be updated with new check-in information
        - The date in the time field must match the date field
        - All check-in information (selfie, time, location, coordinates) will be saved
        - The attendance will be set to "Pending" approval status
        
        **Response:**
        Returns the created or updated attendance record with all details.
        
        **Use Case:**
        Use this endpoint when an employee clicks "Punch In" button in the mobile app after capturing their selfie and location.
        """,
        tags=['Attendance Management'],
        responses={
            201: openapi.Response(
                description="Attendance punched in successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'employee': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'attendance_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                        'attendance_status': openapi.Schema(type=openapi.TYPE_STRING),
                        'check_in_time': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        'check_in_location': openapi.Schema(type=openapi.TYPE_STRING),
                        'check_in_location_latitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'check_in_location_longitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'check_in_selfie': openapi.Schema(type=openapi.TYPE_STRING),
                        'approval_status': openapi.Schema(type=openapi.TYPE_STRING),
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid request data or employee not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['post'], url_path='punch-in')
    def punch_in(self, request):
        """Punch in attendance from mobile app"""
        serializer = AttendancePunchInSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            attendance = serializer.save()
            
            # Return attendance details
            attendance_detail = AttendanceDetailSerializer(attendance, context={'request': request})
            
            return Response({
                **attendance_detail.data,
                'message': 'Attendance punched in successfully'
            }, status=status.HTTP_201_CREATED)
        
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {'error': f'Error processing punch-in: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_id='attendance_punch_out',
        operation_summary="Punch Out Attendance (Mobile App)",
        operation_description="""
        Punch out attendance from mobile app. This endpoint is designed for employees to mark their check-out time using their mobile device.
        
        **What it does:**
        - Accepts check-out time, location, latitude, and longitude
        - Automatically identifies the employee from the authenticated user
        - Updates existing attendance record for today with check-out information
        - Requires that the employee has already punched in for the day
        
        **Required Fields:**
        - time: Check-out time (YYYY-MM-DD HH:MM:SS format)
        - location: Check-out location name or address (string)
        - latitude: Latitude coordinate (decimal, e.g., 23.175017)
        - longitude: Longitude coordinate (decimal, e.g., 72.648375)
        
        **Important Notes:**
        - The employee is automatically identified from the authenticated user's profile
        - An attendance record for today must exist (employee must have punched in first)
        - If no attendance record exists for today, an error will be returned
        - The check-out information will be updated in the existing attendance record
        - The date is automatically extracted from the check-out time
        
        **Response:**
        Returns the updated attendance record with all details including check-in and check-out information.
        
        **Use Case:**
        Use this endpoint when an employee clicks "Punch Out" button in the mobile app after capturing their location.
        """,
        tags=['Attendance Management'],
        responses={
            200: openapi.Response(
                description="Attendance punched out successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'employee': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'attendance_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                        'attendance_status': openapi.Schema(type=openapi.TYPE_STRING),
                        'check_in_time': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        'check_out_time': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        'check_in_location': openapi.Schema(type=openapi.TYPE_STRING),
                        'check_out_location': openapi.Schema(type=openapi.TYPE_STRING),
                        'check_in_location_latitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'check_in_location_longitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'check_out_location_latitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'check_out_location_longitude': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'approval_status': openapi.Schema(type=openapi.TYPE_STRING),
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid request data, employee not found, or no attendance record for today",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['post'], url_path='punch-out')
    def punch_out(self, request):
        """Punch out attendance from mobile app"""
        serializer = AttendancePunchOutSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            attendance = serializer.save()
            
            # Return attendance details
            attendance_detail = AttendanceDetailSerializer(attendance, context={'request': request})
            
            return Response({
                **attendance_detail.data,
                'message': 'Attendance punched out successfully'
            }, status=status.HTTP_200_OK)
        
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {'error': f'Error processing punch-out: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PayrollViewSet(viewsets.ModelViewSet):
    """
    Payroll Management APIs
    """
    queryset = PayrollRecord.objects.select_related(
        'employee', 'employee__profile', 'employee__profile__user',
        'created_by', 'updated_by'
    ).all()
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return PayrollListSerializer
        elif self.action in ['retrieve']:
            return PayrollDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return PayrollCreateSerializer
        elif self.action in ['mark_paid']:
            return PayrollMarkPaidSerializer
        elif self.action in ['bulk_mark_paid']:
            return BulkMarkPayrollPaidSerializer
        return PayrollListSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search by employee name
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(employee__profile__user__first_name__icontains=search) |
                Q(employee__profile__user__last_name__icontains=search) |
                Q(employee__profile__user__username__icontains=search) |
                Q(employee__employee_code__icontains=search)
            )
        
        # Filter by month and year (default to current month and year)
        month_filter = self.request.query_params.get('month', None)
        year_filter = self.request.query_params.get('year', None)
        
        if month_filter and year_filter:
            # Filter by specific month and year
            month = int(month_filter)
            year = int(year_filter)
            # Get first and last day of the month
            first_day = date(year, month, 1)
            last_day = date(year, month, monthrange(year, month)[1])
            queryset = queryset.filter(
                period_from__gte=first_day,
                period_from__lte=last_day
            )
        else:
            # Default to current month and year if no month/year filters are provided
            today = date.today()
            first_day = date(today.year, today.month, 1)
            last_day = date(today.year, today.month, monthrange(today.year, today.month)[1])
            queryset = queryset.filter(
                period_from__gte=first_day,
                period_from__lte=last_day
            )
        
        # Filter by payment status
        payment_status_filter = self.request.query_params.get('payment_status', None)
        if payment_status_filter:
            queryset = queryset.filter(payroll_status=payment_status_filter)
        
        return queryset.order_by('-period_from', '-created_at')
    
    @swagger_auto_schema(
        operation_id='payroll_statistics',
        operation_summary="Get Payroll Management Statistics",
        operation_description="""
        Retrieve statistics for the payroll management dashboard.
        
        **What it returns:**
        - total_payroll: Total payroll amount (sum of all net_amount) for the selected month/year
        - employees_count: Total number of employees with payroll records in the selected month/year
        - total_payment_pending: Number of payroll records with status "Pending" in the selected month/year
        - total_payment_paid: Number of payroll records with status "Paid" in the selected month/year
        
        **Month/Year Filtering:**
        The statistics can be filtered by month and year using query parameters.
        - If month and year are provided, statistics are calculated for that specific month/year
        - If not provided, statistics default to current month and year
        
        **Query Parameters:**
        - month (optional): Filter by month (1-12)
        - year (optional): Filter by year (YYYY)
        
        **Use Case:**
        Use this endpoint to populate dashboard tiles showing key metrics for payroll management.
        """,
        tags=['Payroll Management'],
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
                description="Payroll management statistics",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'total_payroll': openapi.Schema(type=openapi.TYPE_NUMBER, description='Total payroll amount'),
                        'employees_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total number of employees with payroll records'),
                        'total_payment_pending': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of payroll records pending payment'),
                        'total_payment_paid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of payroll records paid')
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """Get payroll management statistics for dashboard"""
        # Get month and year filters (default to current month/year)
        month_filter = request.query_params.get('month', None)
        year_filter = request.query_params.get('year', None)
        
        if month_filter and year_filter:
            month = int(month_filter)
            year = int(year_filter)
            first_day = date(year, month, 1)
            last_day = date(year, month, monthrange(year, month)[1])
        else:
            today = date.today()
            month = today.month
            year = today.year
            first_day = date(year, month, 1)
            last_day = date(year, month, monthrange(year, month)[1])
        
        # Filter payroll records by month and year
        payroll_queryset = PayrollRecord.objects.filter(
            period_from__gte=first_day,
            period_from__lte=last_day
        )
        
        # Total payroll (sum of all net_amount)
        total_payroll = payroll_queryset.aggregate(
            total=Coalesce(Sum('net_amount'), 0)
        )['total'] or 0
        
        # Employees count (unique employees)
        employees_count = payroll_queryset.values('employee').distinct().count()
        
        # Total payment pending
        total_payment_pending = payroll_queryset.filter(
            payroll_status=PayrollRecord.PayrollStatus.PENDING
        ).count()
        
        # Total payment paid
        total_payment_paid = payroll_queryset.filter(
            payroll_status=PayrollRecord.PayrollStatus.PAID
        ).count()
        
        data = {
            'total_payroll': float(total_payroll),
            'employees_count': employees_count,
            'total_payment_pending': total_payment_pending,
            'total_payment_paid': total_payment_paid
        }
        
        serializer = PayrollStatisticsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_id='payroll_list',
        operation_summary="List All Payroll Records",
        operation_description="""
        Retrieve a list of all payroll records with filtering and search options.
        
        **What it returns:**
        - List of payroll records with basic information (employee, period, working days, net amount, payment status)
        - Employee name and code for easy reference
        - Payment date and payment mode if paid
        
        **Search Options:**
        - search: Search by employee name (first name, last name, username) or employee code (case-insensitive partial match)
        
        **Filtering Options:**
        - month: Filter by month (1-12) - must be used with year
        - year: Filter by year (YYYY) - must be used with month
        - payment_status: Filter by payment status (Paid, Pending)
        
        **Default Behavior:**
        - If no month/year filters are provided, results default to current month and year
        
        **Query Parameters:**
        - search (optional): Search by employee name or employee code
        - month (optional): Filter by month (1-12), must be used with year. Defaults to current month if not provided.
        - year (optional): Filter by year (YYYY), must be used with month. Defaults to current year if not provided.
        - payment_status (optional): Filter by payment status (Paid, Pending)
        
        **Pagination:**
        Results are paginated (20 items per page by default) and sorted by period_from date (newest first).
        """,
        tags=['Payroll Management'],
        manual_parameters=[
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description='Search by employee name (first name, last name, username) or employee code',
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
            openapi.Parameter(
                'payment_status',
                openapi.IN_QUERY,
                description='Filter by payment status',
                type=openapi.TYPE_STRING,
                enum=['Paid', 'Pending'],
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of payroll records",
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
        """List all payroll records with filtering and search"""
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='payroll_retrieve',
        operation_summary="Get Payroll Record Details",
        operation_description="""
        Retrieve detailed information about a specific payroll record.
        
        **What it returns:**
        - Complete payroll record information including all payment details
        - Employee information
        - Payment transaction reference if available
        """,
        tags=['Payroll Management'],
        responses={
            200: PayrollDetailSerializer()
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """Get payroll record details"""
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='payroll_create',
        operation_summary="Create Payroll Record",
        operation_description="""
        Create a new payroll record. If a payroll record for the same employee, month, and year already exists, it will be replaced with the new data.
        
        **Required Fields:**
        - employee: ID of the employee
        - payroll_status: Payroll status (Paid, Pending)
        - period_from: Period start date (YYYY-MM-DD)
        - period_to: Period end date (YYYY-MM-DD)
        - working_days: Number of working days
        - days_present: Number of days present
        - net_amount: Net payroll amount
        
        **Optional Fields:**
        - payment_date: Payment date (YYYY-MM-DD) - required if payroll_status is "Paid"
        - payment_mode: Payment mode (Cash, Bank Transfer, Cheque, UPI) - required if payroll_status is "Paid"
        - bank_transaction_reference_number: Bank transaction reference number
        - notes: Additional notes
        
        **Important Notes:**
        - If a payroll record for the same employee, month, and year already exists, it will be replaced with the new data
        - The month and year are determined from the period_from date
        
        **Response:**
        Returns the created or updated payroll record.
        """,
        tags=['Payroll Management'],
        responses={
            200: openapi.Response(
                description="Payroll record updated successfully",
                schema=PayrollCreateSerializer()
            ),
            201: openapi.Response(
                description="Payroll record created successfully",
                schema=PayrollCreateSerializer()
            )
        }
    )
    def create(self, request, *args, **kwargs):
        """Create or update a payroll record"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payroll = serializer.save()
        
        # Check if it was updated or created using the _was_updated flag
        was_updated = getattr(payroll, '_was_updated', False)
        
        if was_updated:
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @swagger_auto_schema(
        operation_id='payroll_update',
        operation_summary="Update Payroll Record",
        operation_description="""
        Update an existing payroll record. All fields are optional - only provided fields will be updated.
        
        **Fields:**
        Same as create endpoint - all fields are optional for update.
        
        **Response:**
        Returns the updated payroll record.
        """,
        tags=['Payroll Management'],
        responses={
            200: openapi.Response(
                description="Payroll record updated successfully",
                schema=PayrollCreateSerializer()
            )
        }
    )
    def update(self, request, *args, **kwargs):
        """Update payroll record information"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        instance.updated_by = request.user
        instance.save()
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_id='payroll_partial_update',
        operation_summary="Partial Update Payroll Record",
        operation_description="""
        Partially update a payroll record. Only provided fields will be updated.
        
        **Use Case:**
        Use this endpoint when you only want to update specific fields without affecting others.
        """,
        tags=['Payroll Management'],
        responses={
            200: openapi.Response(
                description="Payroll record partially updated successfully",
                schema=PayrollCreateSerializer()
            )
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """Partially update payroll record information"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='payroll_delete',
        operation_summary="Delete Payroll Record",
        operation_description="""
        Delete a payroll record from the system. This action is permanent and cannot be undone.
        
        **Use Case:**
        Use this endpoint when you need to permanently remove a payroll record from the system.
        """,
        tags=['Payroll Management'],
        responses={
            204: openapi.Response(description="Payroll record deleted successfully"),
            404: openapi.Response(description="Payroll record not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        """Delete a payroll record"""
        return super().destroy(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='payroll_mark_paid',
        operation_summary="Mark Payroll Record as Paid",
        operation_description="""
        Mark a single payroll record as paid by updating payment details.
        
        **What it does:**
        - Updates the payroll record's status to "Paid"
        - Sets payment_date, payment_mode, and bank_transaction_reference_number
        - Returns the updated payroll record
        
        **Required Fields:**
        - payment_date: Payment date (YYYY-MM-DD)
        - payment_mode: Payment mode (Cash, Bank Transfer, Cheque, UPI)
        
        **Optional Fields:**
        - bank_transaction_reference_number: Bank transaction reference number
        
        **Response:**
        Returns the updated payroll record with payment details.
        """,
        tags=['Payroll Management'],
        responses={
            200: openapi.Response(
                description="Payroll record marked as paid successfully",
                schema=PayrollDetailSerializer()
            ),
            404: openapi.Response(description="Payroll record not found")
        }
    )
    @action(detail=True, methods=['post'], url_path='mark-paid')
    def mark_paid(self, request, pk=None):
        """Mark a payroll record as paid"""
        payroll = self.get_object()
        serializer = PayrollMarkPaidSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                payroll.payroll_status = PayrollRecord.PayrollStatus.PAID
                payroll.payment_date = serializer.validated_data['payment_date']
                payroll.payment_mode = serializer.validated_data['payment_mode']
                payroll.bank_transaction_reference_number = serializer.validated_data.get('bank_transaction_reference_number', None)
                payroll.updated_by = request.user
                payroll.save()
                
                # Notify employee when payroll is paid
                if payroll.employee and payroll.employee.profile and payroll.employee.profile.user:
                    employee_user = payroll.employee.profile.user
                    send_notification_to_user(
                        user=employee_user,
                        title="Payroll Paid",
                        message=f"Your payroll for {payroll.period_from.strftime('%b %Y')} has been paid. Amount: ₹{payroll.net_amount}",
                        notification_type="Payroll",
                        created_by=request.user
                    )
            
            detail_serializer = PayrollDetailSerializer(payroll, context={'request': request})
            return Response(detail_serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {'error': f'Error marking payroll as paid: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(
        operation_id='payroll_bulk_mark_paid',
        operation_summary="Bulk Mark Payroll Records as Paid",
        operation_description="""
        Mark multiple payroll records as paid in bulk. All selected records will be updated with the same payment details.
        
        **What it does:**
        - Accepts a list of payroll record IDs
        - Updates all selected records' status to "Paid"
        - Sets the same payment_date, payment_mode, and bank_transaction_reference_number for all records
        - Returns the number of records updated and any errors
        
        **Request Body:**
        ```json
        {
          "payroll_ids": [1, 2, 3, 4, 5],
          "payment_date": "2024-12-15",
          "payment_mode": "Bank Transfer",
          "bank_transaction_reference_number": "TXN123456"
        }
        ```
        
        **Required Fields:**
        - payroll_ids: List of payroll record IDs to mark as paid
        - payment_date: Payment date (YYYY-MM-DD)
        - payment_mode: Payment mode (Cash, Bank Transfer, Cheque, UPI)
        
        **Optional Fields:**
        - bank_transaction_reference_number: Bank transaction reference number
        
        **Validation:**
        - At least one payroll ID is required
        - Only valid payroll IDs will be processed
        - All operations are performed in a database transaction for data consistency
        
        **Response:**
        Returns the number of records updated, skipped count, and any errors encountered.
        
        **Use Case:**
        Use this endpoint when users select multiple payroll records and click "Mark as Paid" button to process them all at once with the same payment details.
        """,
        tags=['Payroll Management'],
        responses={
            200: openapi.Response(
                description="Payroll records marked as paid successfully",
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
        """Mark multiple payroll records as paid"""
        serializer = BulkMarkPayrollPaidSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        payroll_ids = serializer.validated_data['payroll_ids']
        payment_date = serializer.validated_data['payment_date']
        payment_mode = serializer.validated_data['payment_mode']
        bank_transaction_reference_number = serializer.validated_data.get('bank_transaction_reference_number', None)
        
        if not payroll_ids:
            return Response(
                {'error': 'At least one payroll ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Get all payroll records that exist
                payrolls = PayrollRecord.objects.filter(id__in=payroll_ids)
                
                updated_count = 0
                skipped_count = 0
                errors = []
                
                valid_ids = set(payrolls.values_list('id', flat=True))
                invalid_ids = set(payroll_ids) - valid_ids
                
                if invalid_ids:
                    skipped_count = len(invalid_ids)
                    errors.append(f"Payroll records not found: {', '.join(map(str, invalid_ids))}")
                
                # Update all valid payroll records
                for payroll in payrolls:
                    try:
                        payroll.payroll_status = PayrollRecord.PayrollStatus.PAID
                        payroll.payment_date = payment_date
                        payroll.payment_mode = payment_mode
                        payroll.bank_transaction_reference_number = bank_transaction_reference_number
                        payroll.updated_by = request.user
                        payroll.save()
                        
                        # Notify employee when payroll is paid
                        if payroll.employee and payroll.employee.profile and payroll.employee.profile.user:
                            employee_user = payroll.employee.profile.user
                            send_notification_to_user(
                                user=employee_user,
                                title="Payroll Paid",
                                message=f"Your payroll for {payroll.period_from.strftime('%b %Y')} has been paid. Amount: ₹{payroll.net_amount}",
                                notification_type="Payroll",
                                created_by=request.user
                            )
                        
                        updated_count += 1
                    except Exception as e:
                        errors.append(f"Error updating payroll {payroll.id}: {str(e)}")
                
                return Response({
                    'updated_count': updated_count,
                    'skipped_count': skipped_count,
                    'errors': errors if errors else None
                }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                    {'error': f'Error processing bulk mark as paid: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )


class HolidayCalendarViewSet(viewsets.ModelViewSet):
    """
    Holiday Calendar Management APIs
    """
    queryset = HolidayCalander.objects.select_related('created_by', 'updated_by').all()
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return HolidayCalendarListSerializer
        elif self.action in ['retrieve']:
            return HolidayCalendarDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return HolidayCalendarCreateUpdateSerializer
        elif self.action in ['statistics']:
            return HolidayCalendarStatisticsSerializer
        return HolidayCalendarListSerializer
    
    def get_queryset(self):
        """Return holidays with filtering and search"""
        queryset = super().get_queryset()
        
        # Search by holiday name
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        # Filter by holiday type
        holiday_type_filter = self.request.query_params.get('type', None)
        if holiday_type_filter:
            queryset = queryset.filter(type=holiday_type_filter)
        
        # Filter by year (default to current year if not specified)
        year_filter = self.request.query_params.get('year', None)
        if year_filter:
            try:
                year = int(year_filter)
                queryset = queryset.filter(date__year=year)
            except ValueError:
                pass
        else:
            # Default to current year if no year filter
            from datetime import date
            current_year = date.today().year
            queryset = queryset.filter(date__year=current_year)
        
        return queryset.order_by('date')
    
    @swagger_auto_schema(
        operation_id='holiday_calendar_statistics',
        operation_summary="Get Holiday Calendar Dashboard Statistics",
        operation_description="""
        Retrieve statistics for the Holiday Calendar dashboard tiles.
        
        **What it returns:**
        - total_holidays: Total number of holidays in the current year
        - public_holidays: Number of public holidays (National) in the current year
        - optional_holidays: Number of optional holidays (Festival) in the current year
        
        **Holiday Types:**
        - National: Public holidays (mandatory for all employees)
        - Festival: Optional holidays (employees can choose to work)
        - Company: Company-specific holidays
        
        **Calculation:**
        - Statistics are calculated for the current year
        - Public holidays = National holidays
        - Optional holidays = Festival holidays
        - Total holidays = All holidays (National + Festival + Company)
        
        **Use Case:**
        Use this endpoint to populate dashboard tiles showing key metrics for holiday calendar.
        """,
        tags=['Holiday Calendar Dashboard'],
        responses={
            200: openapi.Response(
                description="Holiday calendar statistics",
                schema=HolidayCalendarStatisticsSerializer()
            )
        }
    )
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """Get holiday calendar statistics for dashboard"""
        from datetime import date
        
        today = date.today()
        current_year = today.year
        
        # Get all holidays for current year
        holidays_queryset = HolidayCalander.objects.filter(
            date__year=current_year
        )
        
        # Total holidays
        total_holidays = holidays_queryset.count()
        
        # Public holidays (National)
        public_holidays = holidays_queryset.filter(
            type=HolidayCalander.HolidayType.NATIONAL
        ).count()
        
        # Optional holidays (Festival)
        optional_holidays = holidays_queryset.filter(
            type=HolidayCalander.HolidayType.FESTIVAL
        ).count()
        
        data = {
            'total_holidays': total_holidays,
            'public_holidays': public_holidays,
            'optional_holidays': optional_holidays
        }
        
        serializer = HolidayCalendarStatisticsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_id='holiday_calendar_list',
        operation_summary="List All Holidays",
        operation_description="""
        Retrieve a list of all holidays with filtering options.
        
        **What it returns:**
        - List of holidays with basic information (name, date, type)
        
        **Search Options:**
        - search: Search by holiday name (case-insensitive partial match)
        
        **Filtering Options:**
        - type: Filter by holiday type (National, Festival, Company)
        - year: Filter by year (defaults to current year if not specified)
        
        **Query Parameters:**
        - search (optional): Search by holiday name
        - type (optional): Filter by holiday type (National, Festival, Company)
        - year (optional): Filter by year (YYYY format, defaults to current year)
        
        **Pagination:**
        Results are paginated (20 items per page by default) and sorted by date (earliest first).
        """,
        tags=['Holiday Calendar Dashboard'],
        manual_parameters=[
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description='Search by holiday name',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'type',
                openapi.IN_QUERY,
                description='Filter by holiday type',
                type=openapi.TYPE_STRING,
                enum=['National', 'Festival', 'Company'],
                required=False
            ),
            openapi.Parameter(
                'year',
                openapi.IN_QUERY,
                description='Filter by year (YYYY format, defaults to current year)',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of holidays",
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
        """List all holidays with filtering"""
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='holiday_calendar_retrieve',
        operation_summary="Get Holiday Details",
        operation_description="""
        Retrieve detailed information about a specific holiday.
        """,
        tags=['Holiday Calendar Dashboard'],
        responses={
            200: HolidayCalendarDetailSerializer(),
            404: openapi.Response(description="Holiday not found")
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """Get holiday details"""
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='holiday_calendar_create',
        operation_summary="Create Holiday Entry",
        operation_description="""
        Create a new holiday entry.
        
        **Required Fields:**
        - name: Holiday Name
        - date: Holiday Date (YYYY-MM-DD format)
        - type: Holiday Type (National, Festival, Company)
        
        **Validation:**
        - Date must be unique (only one holiday per date allowed)
        - Holiday type must be one of: National, Festival, Company
        
        **Response:**
        Returns the created holiday entry.
        """,
        tags=['Holiday Calendar Dashboard'],
        request_body=HolidayCalendarCreateUpdateSerializer,
        responses={
            201: openapi.Response(
                description="Holiday created successfully",
                schema=HolidayCalendarCreateUpdateSerializer()
            ),
            400: openapi.Response(description="Invalid request data (e.g., duplicate date)")
        }
    )
    def create(self, request, *args, **kwargs):
        """Create a new holiday entry"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @swagger_auto_schema(
        operation_id='holiday_calendar_update',
        operation_summary="Update Holiday Entry",
        operation_description="""
        Update an existing holiday entry. All fields are optional - only provided fields will be updated.
        
        **Fields:**
        Same as create endpoint - all fields are optional for update.
        
        **Note:**
        - If date is updated, it must still be unique
        - If type is updated, it must be one of: National, Festival, Company
        
        **Response:**
        Returns the updated holiday entry.
        """,
        tags=['Holiday Calendar Dashboard'],
        request_body=HolidayCalendarCreateUpdateSerializer,
        responses={
            200: openapi.Response(
                description="Holiday updated successfully",
                schema=HolidayCalendarCreateUpdateSerializer()
            )
        }
    )
    def update(self, request, *args, **kwargs):
        """Update holiday entry information"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_id='holiday_calendar_partial_update',
        operation_summary="Partial Update Holiday Entry",
        operation_description="""
        Partially update a holiday entry's information. Only provided fields will be updated.
        """,
        tags=['Holiday Calendar Dashboard'],
        request_body=HolidayCalendarCreateUpdateSerializer,
        responses={
            200: openapi.Response(
                description="Holiday partially updated successfully",
                schema=HolidayCalendarCreateUpdateSerializer()
            )
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """Partially update holiday entry information"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='holiday_calendar_delete',
        operation_summary="Delete Holiday Entry",
        operation_description="""
        Delete a holiday entry from the system. This action is permanent and cannot be undone.
        """,
        tags=['Holiday Calendar Dashboard'],
        responses={
            204: openapi.Response(description="Holiday deleted successfully"),
            404: openapi.Response(description="Holiday not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        """Delete a holiday entry"""
        return super().destroy(request, *args, **kwargs)

