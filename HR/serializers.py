from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Employee, Attendance, ContractWorker, PayrollRecord, HolidayCalander
from Profiles.models import Profile, MobileNumber
from Accounts.models import BankAccount


class EmployeeListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    availability_status = serializers.SerializerMethodField()
    profile_id = serializers.IntegerField(source='profile.id', read_only=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'employee_code', 'profile_id', 'full_name', 'email', 'phone_number',
            'photo_url', 'designation', 'availability_status', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_full_name(self, obj):
        """Get full name from profile user"""
        if obj.profile and obj.profile.user:
            user = obj.profile.user
            full_name = f"{user.first_name} {user.last_name}".strip()
            return full_name if full_name else user.username
        return None
    
    def get_email(self, obj):
        """Get email from profile user"""
        if obj.profile and obj.profile.user:
            return obj.profile.user.email
        return None
    
    def get_phone_number(self, obj):
        """Get phone number from MobileNumber model"""
        if obj.profile and obj.profile.user:
            # Get primary mobile number or first mobile number
            mobile = obj.profile.user.mobile_numbers.filter(is_primary=True).first()
            if not mobile:
                mobile = obj.profile.user.mobile_numbers.first()
            if mobile:
                return mobile.mobile_number
        return None
    
    def get_photo_url(self, obj):
        """Get photo URL from profile"""
        if obj.profile and obj.profile.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile.photo.url)
            return obj.profile.photo.url
        return None
    
    def get_availability_status(self, obj):
        """Get today's attendance status (Present/Absent)"""
        from datetime import date
        today = date.today()
        try:
            attendance = obj.attendance_records.filter(attendance_date=today).first()
            if attendance:
                return attendance.attendance_status
        except:
            pass
        return None


class EmployeeDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    date_of_birth = serializers.SerializerMethodField()
    gender = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    pin_code = serializers.SerializerMethodField()
    country = serializers.SerializerMethodField()
    aadhar_number = serializers.SerializerMethodField()
    pan_number = serializers.SerializerMethodField()
    aadhar_card_url = serializers.SerializerMethodField()
    pan_card_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Employee
        fields = [
            'id', 'employee_code', 'full_name', 'email', 'phone_number',
            'photo_url', 'date_of_birth', 'gender', 'address', 'city',
            'state', 'pin_code', 'country', 'aadhar_number', 'pan_number',
            'aadhar_card_url', 'pan_card_url', 'designation', 'joining_date',
            'monthly_salary', 'profile', 'created_at', 'updated_at',
            'created_by', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def get_full_name(self, obj):
        """Get full name from profile user"""
        if obj.profile and obj.profile.user:
            user = obj.profile.user
            full_name = f"{user.first_name} {user.last_name}".strip()
            return full_name if full_name else user.username
        return None
    
    def get_email(self, obj):
        """Get email from profile user"""
        if obj.profile and obj.profile.user:
            return obj.profile.user.email
        return None
    
    def get_phone_number(self, obj):
        """Get phone number from MobileNumber model"""
        if obj.profile and obj.profile.user:
            # Get primary mobile number or first mobile number
            mobile = obj.profile.user.mobile_numbers.filter(is_primary=True).first()
            if not mobile:
                mobile = obj.profile.user.mobile_numbers.first()
            if mobile:
                return mobile.mobile_number
        return None
    
    def get_date_of_birth(self, obj):
        """Get date of birth from profile"""
        return obj.profile.date_of_birth if obj.profile else None
    
    def get_gender(self, obj):
        """Get gender from profile"""
        return obj.profile.gender if obj.profile else None
    
    def get_photo_url(self, obj):
        """Get photo URL from profile"""
        if obj.profile and obj.profile.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile.photo.url)
            return obj.profile.photo.url
        return None
    
    def get_address(self, obj):
        """Get address from profile"""
        return obj.profile.address if obj.profile else None
    
    def get_city(self, obj):
        """Get city from profile"""
        return obj.profile.city if obj.profile else None
    
    def get_state(self, obj):
        """Get state from profile"""
        return obj.profile.state if obj.profile else None
    
    def get_pin_code(self, obj):
        """Get pin_code from profile"""
        return obj.profile.pin_code if obj.profile else None
    
    def get_country(self, obj):
        """Get country from profile"""
        return obj.profile.country if obj.profile else None
    
    def get_aadhar_number(self, obj):
        """Get aadhar number - Note: Profile model doesn't have this field, returning None"""
        # Profile model only has aadhar_card (file), not aadhar_number (text)
        # If you need to store aadhar_number, add it to Profile model
        return None
    
    def get_pan_number(self, obj):
        """Get pan number - Note: Profile model doesn't have this field, returning None"""
        # Profile model only has pan_card (file), not pan_number (text)
        # If you need to store pan_number, add it to Profile model
        return None
    
    def get_aadhar_card_url(self, obj):
        """Get aadhar card URL from profile"""
        if obj.profile and obj.profile.aadhar_card:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile.aadhar_card.url)
            return obj.profile.aadhar_card.url
        return None
    
    def get_pan_card_url(self, obj):
        """Get pan card URL from profile"""
        if obj.profile and obj.profile.pan_card:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile.pan_card.url)
            return obj.profile.pan_card.url
        return None


class EmployeeCreateSerializer(serializers.ModelSerializer):
    # Profile/User fields
    first_name = serializers.CharField(write_only=True, required=True)
    last_name = serializers.CharField(write_only=True, required=True)
    email = serializers.EmailField(write_only=True, required=True)
    phone_number = serializers.CharField(write_only=True, required=True)
    photo = serializers.ImageField(write_only=True, required=False, allow_null=True)
    date_of_birth = serializers.DateField(write_only=True, required=False, allow_null=True)
    gender = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    address = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    city = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    state = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    pin_code = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    country = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    aadhar_number = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    pan_number = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    aadhar_card = serializers.FileField(write_only=True, required=False, allow_null=True)
    pan_card = serializers.FileField(write_only=True, required=False, allow_null=True)
    
    # Employee fields
    employee_code = serializers.CharField(required=True)
    designation = serializers.ChoiceField(choices=Employee.Designation.choices, required=True)
    joining_date = serializers.DateField(required=True)
    monthly_salary = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'employee_code', 'first_name', 'last_name', 'email', 'phone_number',
            'photo', 'date_of_birth', 'gender', 'address', 'city', 'state',
            'pin_code', 'country', 'aadhar_number', 'pan_number', 'aadhar_card',
            'pan_card', 'designation', 'joining_date', 'monthly_salary'
        ]
        read_only_fields = ['id']
    
    def create(self, validated_data):
        from django.db import transaction
        
        # Extract profile/user fields
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        email = validated_data.pop('email')
        phone_number = validated_data.pop('phone_number')
        photo = validated_data.pop('photo', None)
        date_of_birth = validated_data.pop('date_of_birth', None)
        gender = validated_data.pop('gender', None)
        address = validated_data.pop('address', None)
        city = validated_data.pop('city', None)
        state = validated_data.pop('state', None)
        pin_code = validated_data.pop('pin_code', None)
        country = validated_data.pop('country', None)
        aadhar_number = validated_data.pop('aadhar_number', None)
        pan_number = validated_data.pop('pan_number', None)
        aadhar_card = validated_data.pop('aadhar_card', None)
        pan_card = validated_data.pop('pan_card', None)
        
        # Extract employee fields
        employee_code = validated_data.pop('employee_code')
        designation = validated_data.pop('designation')
        joining_date = validated_data.pop('joining_date')
        monthly_salary = validated_data.pop('monthly_salary')
        
        request_user = self.context['request'].user
        
        with transaction.atomic():
            # Create user
            username = email or f"employee_{Employee.objects.count() + 1}"
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
            
            # Set password to phone_number (mobile number)
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=phone_number
            )
            
            # Create profile
            profile = Profile.objects.create(
                user=user,
                photo=photo,
                date_of_birth=date_of_birth,
                gender=gender,
                address=address,
                city=city,
                state=state,
                pin_code=pin_code,
                country=country,
                aadhar_number=aadhar_number,
                pan_number=pan_number,
                aadhar_card=aadhar_card,
                pan_card=pan_card,
                created_by=request_user if request_user.is_authenticated else None
            )
            
            # Create employee
            employee = Employee.objects.create(
                profile=profile,
                employee_code=employee_code,
                designation=designation,
                joining_date=joining_date,
                monthly_salary=monthly_salary,
                created_by=request_user if request_user.is_authenticated else None
            )
            
            # Create mobile number if provided
            if phone_number:
                phone_number_cleaned = str(phone_number).strip()
                if phone_number_cleaned:
                    try:
                        # Check if mobile number already exists for another user
                        existing_mobile = MobileNumber.objects.filter(mobile_number=phone_number_cleaned).first()
                        if existing_mobile:
                            # If exists for different user, raise error
                            if existing_mobile.user != user:
                                raise serializers.ValidationError({
                                    'phone_number': 'This mobile number is already associated with another user.'
                                })
                            # If exists for same user, update it to be primary
                            existing_mobile.is_primary = True
                            existing_mobile.updated_by = request_user if request_user.is_authenticated else None
                            existing_mobile.save()
                        else:
                            # Mark any existing mobile numbers for this user as non-primary
                            MobileNumber.objects.filter(user=user).update(is_primary=False)
                            # Create new mobile number as primary
                            MobileNumber.objects.create(
                                user=user,
                                mobile_number=phone_number_cleaned,
                                is_primary=True,
                                created_by=request_user if request_user.is_authenticated else None
                            )
                    except Exception as e:
                        # Log the error and re-raise with a more user-friendly message
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Error creating mobile number for employee: {str(e)}")
                        raise serializers.ValidationError({
                            'phone_number': f'Failed to save mobile number: {str(e)}'
                        })
            
            return employee
    
    def update(self, instance, validated_data):
        from django.db import transaction
        
        # Extract profile/user fields
        first_name = validated_data.pop('first_name', None)
        last_name = validated_data.pop('last_name', None)
        email = validated_data.pop('email', None)
        phone_number = validated_data.pop('phone_number', None)
        photo = validated_data.pop('photo', None)
        date_of_birth = validated_data.pop('date_of_birth', None)
        gender = validated_data.pop('gender', None)
        address = validated_data.pop('address', None)
        city = validated_data.pop('city', None)
        state = validated_data.pop('state', None)
        pin_code = validated_data.pop('pin_code', None)
        country = validated_data.pop('country', None)
        aadhar_number = validated_data.pop('aadhar_number', None)
        pan_number = validated_data.pop('pan_number', None)
        aadhar_card = validated_data.pop('aadhar_card', None)
        pan_card = validated_data.pop('pan_card', None)
        
        with transaction.atomic():
            # Update user
            if instance.profile and instance.profile.user:
                user = instance.profile.user
                if first_name:
                    user.first_name = first_name
                if last_name:
                    user.last_name = last_name
                if email:
                    user.email = email
                user.save()
            
            # Update profile
            if instance.profile:
                profile = instance.profile
                if photo is not None:
                    profile.photo = photo
                if date_of_birth is not None:
                    profile.date_of_birth = date_of_birth
                if gender is not None:
                    profile.gender = gender
                if address is not None:
                    profile.address = address
                if city is not None:
                    profile.city = city
                if state is not None:
                    profile.state = state
                if pin_code is not None:
                    profile.pin_code = pin_code
                if country is not None:
                    profile.country = country
                if aadhar_number is not None:
                    profile.aadhar_number = aadhar_number
                if pan_number is not None:
                    profile.pan_number = pan_number
                if aadhar_card is not None:
                    profile.aadhar_card = aadhar_card
                if pan_card is not None:
                    profile.pan_card = pan_card
                user = self.context['request'].user
                profile.updated_by = user if user.is_authenticated else None
                profile.save()
            
            # Update mobile number if provided
            if phone_number is not None:
                if instance.profile and instance.profile.user:
                    user = instance.profile.user
                    request_user = self.context['request'].user
                    
                    phone_number_cleaned = str(phone_number).strip() if phone_number else ""
                    if phone_number_cleaned:
                        try:
                            # Check if mobile number already exists for another user
                            existing_mobile = MobileNumber.objects.filter(mobile_number=phone_number_cleaned).first()
                            if existing_mobile:
                                # If exists for different user, raise error
                                if existing_mobile.user != user:
                                    raise serializers.ValidationError({
                                        'phone_number': 'This mobile number is already associated with another user.'
                                    })
                                # If exists for same user, update it to be primary
                                existing_mobile.is_primary = True
                                existing_mobile.updated_by = request_user if request_user.is_authenticated else None
                                existing_mobile.save()
                            else:
                                # Mark any existing mobile numbers for this user as non-primary
                                MobileNumber.objects.filter(user=user).update(is_primary=False)
                                # Create new mobile number as primary
                                MobileNumber.objects.create(
                                    user=user,
                                    mobile_number=phone_number_cleaned,
                                    is_primary=True,
                                    created_by=request_user if request_user.is_authenticated else None
                                )
                        except Exception as e:
                            # Log the error and re-raise with a more user-friendly message
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(f"Error updating mobile number for employee: {str(e)}")
                            raise serializers.ValidationError({
                                'phone_number': f'Failed to save mobile number: {str(e)}'
                            })
                    else:
                        # If phone_number is empty, remove primary status from all mobile numbers
                        MobileNumber.objects.filter(user=user).update(is_primary=False)
            
            # Update employee
            user = self.context['request'].user
            validated_data['updated_by'] = user if user.is_authenticated else None
            return super().update(instance, validated_data)


class EmployeeStatisticsSerializer(serializers.Serializer):
    total_employees = serializers.IntegerField()
    total_present = serializers.IntegerField()
    total_absent = serializers.IntegerField()
    monthly_payroll = serializers.DecimalField(max_digits=15, decimal_places=2)


# Contract Worker Serializers
class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ['id', 'bank_name', 'account_number', 'ifsc_code', 'branch']
        read_only_fields = ['id']


class ContractWorkerListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    availability_status = serializers.SerializerMethodField()
    project_name = serializers.CharField(source='project.name', read_only=True, allow_null=True)
    
    class Meta:
        model = ContractWorker
        fields = [
            'id', 'full_name', 'email', 'phone_number', 'worker_type',
            'availability_status', 'project', 'project_name', 'monthly_salary',
            'department', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_full_name(self, obj):
        """Get full name from profile user"""
        if obj.profile and obj.profile.user:
            user = obj.profile.user
            full_name = f"{user.first_name} {user.last_name}".strip()
            return full_name if full_name else user.username
        return None
    
    def get_email(self, obj):
        """Get email from profile user"""
        if obj.profile and obj.profile.user:
            return obj.profile.user.email
        return None
    
    def get_phone_number(self, obj):
        """Get phone number - would need to be stored separately"""
        return None
    
    def get_availability_status(self, obj):
        """Get availability status (assigned/available)"""
        if obj.project:
            return 'assigned'
        return 'available'


class ContractWorkerDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    date_of_birth = serializers.SerializerMethodField()
    gender = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    pin_code = serializers.SerializerMethodField()
    country = serializers.SerializerMethodField()
    project_name = serializers.CharField(source='project.name', read_only=True, allow_null=True)
    bank_account = serializers.SerializerMethodField()
    
    class Meta:
        model = ContractWorker
        fields = [
            'id', 'full_name', 'email', 'phone_number', 'date_of_birth', 'gender',
            'address', 'city', 'state', 'pin_code', 'country', 'worker_type',
            'monthly_salary', 'aadhar_no', 'uan_number', 'department',
            'project', 'project_name', 'bank_account', 'profile',
            'created_at', 'updated_at', 'created_by', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def get_full_name(self, obj):
        """Get full name from profile user"""
        if obj.profile and obj.profile.user:
            user = obj.profile.user
            full_name = f"{user.first_name} {user.last_name}".strip()
            return full_name if full_name else user.username
        return None
    
    def get_email(self, obj):
        """Get email from profile user"""
        if obj.profile and obj.profile.user:
            return obj.profile.user.email
        return None
    
    def get_phone_number(self, obj):
        """Get phone number - would need to be stored separately"""
        return None
    
    def get_date_of_birth(self, obj):
        """Get date of birth from profile"""
        return obj.profile.date_of_birth if obj.profile else None
    
    def get_gender(self, obj):
        """Get gender from profile"""
        return obj.profile.gender if obj.profile else None
    
    def get_address(self, obj):
        """Get address from profile"""
        return obj.profile.address if obj.profile else None
    
    def get_city(self, obj):
        """Get city from profile"""
        return obj.profile.city if obj.profile else None
    
    def get_state(self, obj):
        """Get state from profile"""
        return obj.profile.state if obj.profile else None
    
    def get_pin_code(self, obj):
        """Get pin_code from profile"""
        return obj.profile.pin_code if obj.profile else None
    
    def get_country(self, obj):
        """Get country from profile"""
        return obj.profile.country if obj.profile else None
    
    def get_bank_account(self, obj):
        """Get bank account details"""
        if obj.profile:
            bank_account = obj.profile.bank_accounts.first()
            if bank_account:
                return BankAccountSerializer(bank_account, context=self.context).data
        return None


class ContractWorkerCreateSerializer(serializers.ModelSerializer):
    # Profile/User fields
    first_name = serializers.CharField(write_only=True, required=True)
    last_name = serializers.CharField(write_only=True, required=True)
    email = serializers.EmailField(write_only=True, required=True)
    phone_number = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    date_of_birth = serializers.DateField(write_only=True, required=False, allow_null=True)
    gender = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    address = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    city = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    state = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    pin_code = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    country = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    
    # Bank Account fields
    bank_name = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    bank_account_number = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    ifsc_code = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    bank_branch = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    
    # ContractWorker fields
    worker_type = serializers.ChoiceField(choices=ContractWorker.WorkerType.choices, required=True)
    monthly_salary = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)
    aadhar_no = serializers.CharField(required=True)
    uan_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    department = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    class Meta:
        model = ContractWorker
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone_number',
            'date_of_birth', 'gender', 'address', 'city', 'state',
            'pin_code', 'country', 'worker_type', 'monthly_salary',
            'aadhar_no', 'uan_number', 'department', 'project',
            'bank_name', 'bank_account_number', 'ifsc_code', 'bank_branch'
        ]
        read_only_fields = ['id']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set queryset for project field
        from Projects.models import Project
        self.fields['project'] = serializers.PrimaryKeyRelatedField(
            queryset=Project.objects.all(),
            required=False,
            allow_null=True
        )
    
    def create(self, validated_data):
        from django.db import transaction
        
        # Extract profile/user fields
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        email = validated_data.pop('email')
        phone_number = validated_data.pop('phone_number', None)
        date_of_birth = validated_data.pop('date_of_birth', None)
        gender = validated_data.pop('gender', None)
        address = validated_data.pop('address', None)
        city = validated_data.pop('city', None)
        state = validated_data.pop('state', None)
        pin_code = validated_data.pop('pin_code', None)
        country = validated_data.pop('country', None)
        
        # Extract bank account fields
        bank_name = validated_data.pop('bank_name', None)
        bank_account_number = validated_data.pop('bank_account_number', None)
        ifsc_code = validated_data.pop('ifsc_code', None)
        bank_branch = validated_data.pop('bank_branch', None)
        
        # Extract contract worker fields
        worker_type = validated_data.pop('worker_type')
        monthly_salary = validated_data.pop('monthly_salary')
        aadhar_no = validated_data.pop('aadhar_no')
        uan_number = validated_data.pop('uan_number', None)
        department = validated_data.pop('department', None)
        project = validated_data.pop('project', None)
        
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
                created_by=self.context['request'].user
            )
            
            # Create bank account if bank details provided
            if bank_name and bank_account_number and ifsc_code:
                BankAccount.objects.create(
                    profile=profile,
                    bank_name=bank_name,
                    account_number=bank_account_number,
                    ifsc_code=ifsc_code,
                    branch=bank_branch,
                    created_by=self.context['request'].user
                )
            
            # Create contract worker
            contract_worker = ContractWorker.objects.create(
                profile=profile,
                project=project,
                worker_type=worker_type,
                monthly_salary=monthly_salary,
                aadhar_no=aadhar_no,
                uan_number=uan_number,
                department=department,
                created_by=self.context['request'].user
            )
            
            return contract_worker
    
    def update(self, instance, validated_data):
        from django.db import transaction
        
        # Extract profile/user fields
        first_name = validated_data.pop('first_name', None)
        last_name = validated_data.pop('last_name', None)
        email = validated_data.pop('email', None)
        phone_number = validated_data.pop('phone_number', None)
        date_of_birth = validated_data.pop('date_of_birth', None)
        gender = validated_data.pop('gender', None)
        address = validated_data.pop('address', None)
        city = validated_data.pop('city', None)
        state = validated_data.pop('state', None)
        pin_code = validated_data.pop('pin_code', None)
        country = validated_data.pop('country', None)
        
        # Extract bank account fields
        bank_name = validated_data.pop('bank_name', None)
        bank_account_number = validated_data.pop('bank_account_number', None)
        ifsc_code = validated_data.pop('ifsc_code', None)
        bank_branch = validated_data.pop('bank_branch', None)
        
        with transaction.atomic():
            # Update user
            if instance.profile and instance.profile.user:
                user = instance.profile.user
                if first_name:
                    user.first_name = first_name
                if last_name:
                    user.last_name = last_name
                if email:
                    user.email = email
                user.save()
            
            # Update profile
            if instance.profile:
                profile = instance.profile
                if date_of_birth is not None:
                    profile.date_of_birth = date_of_birth
                if gender is not None:
                    profile.gender = gender
                if address is not None:
                    profile.address = address
                if city is not None:
                    profile.city = city
                if state is not None:
                    profile.state = state
                if pin_code is not None:
                    profile.pin_code = pin_code
                if country is not None:
                    profile.country = country
                profile.updated_by = self.context['request'].user
                profile.save()
                
                # Update or create bank account
                if bank_name and bank_account_number and ifsc_code:
                    bank_account, created = BankAccount.objects.get_or_create(
                        profile=profile,
                        defaults={
                            'bank_name': bank_name,
                            'account_number': bank_account_number,
                            'ifsc_code': ifsc_code,
                            'branch': bank_branch,
                            'created_by': self.context['request'].user
                        }
                    )
                    if not created:
                        bank_account.bank_name = bank_name
                        bank_account.account_number = bank_account_number
                        bank_account.ifsc_code = ifsc_code
                        bank_account.branch = bank_branch
                        user = self.context['request'].user
                        bank_account.updated_by = user if user.is_authenticated else None
                        bank_account.save()
            
            # Update contract worker
            user = self.context['request'].user
            validated_data['updated_by'] = user if user.is_authenticated else None
            return super().update(instance, validated_data)


class ContractWorkerStatisticsSerializer(serializers.Serializer):
    total_workers = serializers.IntegerField()
    total_available = serializers.IntegerField()
    total_assigned = serializers.IntegerField()
    total_monthly_payroll = serializers.DecimalField(max_digits=15, decimal_places=2)


class BulkUploadContractWorkerSerializer(serializers.Serializer):
    excel_file = serializers.FileField(required=True, help_text='Excel file (.xlsx or .xls) with contract worker data')


# Attendance Serializers
class AttendanceListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    
    class Meta:
        model = Attendance
        fields = [
            'id', 'employee', 'employee_name', 'employee_code', 'attendance_date',
            'attendance_status', 'approval_status', 'check_in_time', 'check_out_time',
            'notes', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_employee_name(self, obj):
        """Get employee name from profile user"""
        if obj.employee and obj.employee.profile and obj.employee.profile.user:
            user = obj.employee.profile.user
            full_name = f"{user.first_name} {user.last_name}".strip()
            return full_name if full_name else user.username
        return None


class AttendanceDetailSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    check_in_selfie_url = serializers.SerializerMethodField()
    check_out_selfie_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Attendance
        fields = [
            'id', 'employee', 'employee_name', 'employee_code', 'attendance_date',
            'attendance_status', 'approval_status', 'rejection_reason',
            'check_in_time', 'check_out_time', 'check_in_location', 'check_out_location',
            'check_in_location_latitude', 'check_in_location_longitude',
            'check_out_location_latitude', 'check_out_location_longitude',
            'check_in_selfie', 'check_in_selfie_url', 'check_out_selfie', 'check_out_selfie_url',
            'notes', 'created_at', 'updated_at', 'created_by', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def get_employee_name(self, obj):
        """Get employee name from profile user"""
        if obj.employee and obj.employee.profile and obj.employee.profile.user:
            user = obj.employee.profile.user
            full_name = f"{user.first_name} {user.last_name}".strip()
            return full_name if full_name else user.username
        return None
    
    def get_check_in_selfie_url(self, obj):
        """Get check-in selfie URL"""
        if obj.check_in_selfie:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.check_in_selfie.url)
            return obj.check_in_selfie.url
        return None
    
    def get_check_out_selfie_url(self, obj):
        """Get check-out selfie URL"""
        if obj.check_out_selfie:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.check_out_selfie.url)
            return obj.check_out_selfie.url
        return None


class AttendanceCreateSerializer(serializers.ModelSerializer):
    was_created = serializers.BooleanField(read_only=True, help_text='Indicates if the record was newly created (True) or updated (False)')
    
    class Meta:
        model = Attendance
        fields = [
            'id', 'employee', 'attendance_date', 'attendance_status',
            'check_in_time', 'check_out_time', 'notes', 'was_created'
        ]
        read_only_fields = ['id', 'was_created']
    
    def create(self, validated_data):
        """Create or update attendance record"""
        user = self.context['request'].user
        employee = validated_data.get('employee')
        attendance_date = validated_data.get('attendance_date')
        
        # Get or create attendance record
        attendance, created = Attendance.objects.get_or_create(
            employee=employee,
            attendance_date=attendance_date,
            defaults={
                'attendance_status': validated_data.get('attendance_status'),
                'check_in_time': validated_data.get('check_in_time', None),
                'check_out_time': validated_data.get('check_out_time', None),
                'notes': validated_data.get('notes', None),
                'created_by': user if user.is_authenticated else None,
                'approval_status': Attendance.ApprovalStatus.PENDING
            }
        )
        
        # If record already exists, update it
        if not created:
            user = self.context['request'].user
            attendance.attendance_status = validated_data.get('attendance_status')
            attendance.check_in_time = validated_data.get('check_in_time', None)
            attendance.check_out_time = validated_data.get('check_out_time', None)
            attendance.notes = validated_data.get('notes', None)
            attendance.updated_by = user if user.is_authenticated else None
            attendance.approval_status = Attendance.ApprovalStatus.PENDING  # Reset to pending when updated
            attendance.save()
        
        # Store whether it was created for use in to_representation
        attendance._was_created = created
        return attendance
    
    def to_representation(self, instance):
        """Add was_created field to response"""
        representation = super().to_representation(instance)
        representation['was_created'] = getattr(instance, '_was_created', False)
        return representation


class AttendanceStatisticsSerializer(serializers.Serializer):
    total_working_days = serializers.IntegerField()
    total_employees_present = serializers.IntegerField()
    total_employees_absent = serializers.IntegerField()
    total_pending_approvals = serializers.IntegerField()


class BulkApproveAttendanceSerializer(serializers.Serializer):
    attendance_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text='List of attendance record IDs to approve/reject'
    )
    approval_status = serializers.ChoiceField(
        choices=Attendance.ApprovalStatus.choices,
        help_text='Approval status: Approved or Rejected'
    )
    rejection_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text='Rejection reason (required if approval_status is Rejected)'
    )
    
    def validate(self, attrs):
        approval_status = attrs.get('approval_status')
        rejection_reason = attrs.get('rejection_reason')
        
        if approval_status == Attendance.ApprovalStatus.REJECTED and not rejection_reason:
            raise serializers.ValidationError({
                'rejection_reason': 'Rejection reason is required when approval_status is Rejected'
            })
        
        return attrs


class AttendancePunchInSerializer(serializers.Serializer):
    selfie = serializers.ImageField(required=True, help_text='Selfie image captured during punch-in')
    date = serializers.DateField(required=True, help_text='Date of attendance (YYYY-MM-DD)')
    time = serializers.DateTimeField(required=True, help_text='Check-in time (YYYY-MM-DD HH:MM:SS)')
    location = serializers.CharField(required=True, max_length=255, help_text='Location name/address')
    latitude = serializers.DecimalField(required=True, max_digits=9, decimal_places=6, help_text='Latitude coordinate')
    longitude = serializers.DecimalField(required=True, max_digits=9, decimal_places=6, help_text='Longitude coordinate')
    
    def validate(self, attrs):
        """Validate that date and time are consistent"""
        date = attrs.get('date')
        time = attrs.get('time')
        
        if date and time:
            if date != time.date():
                raise serializers.ValidationError({
                    'time': 'The date in time field must match the date field'
                })
        
        return attrs
    
    def create(self, validated_data):
        """Create attendance record from punch-in data"""
        from django.db import transaction
        from datetime import datetime, date
        
        request = self.context['request']
        user = request.user
        
        # Get employee from user
        try:
            employee = Employee.objects.get(profile__user=user)
        except Employee.DoesNotExist:
            raise serializers.ValidationError({
                'employee': ['Employee record not found for this user. Please contact administrator.']
            })
        except Employee.MultipleObjectsReturned:
            employee = Employee.objects.filter(profile__user=user).first()
        
        selfie = validated_data.get('selfie')
        attendance_date = validated_data.get('date')
        check_in_time = validated_data.get('time')
        location = validated_data.get('location')
        latitude = validated_data.get('latitude')
        longitude = validated_data.get('longitude')
        
        with transaction.atomic():
            # Get or create attendance record
            attendance, created = Attendance.objects.get_or_create(
                employee=employee,
                attendance_date=attendance_date,
                defaults={
                    'attendance_status': Attendance.AttendanceStatus.PRESENT,
                    'check_in_time': check_in_time,
                    'check_in_location': location,
                    'check_in_location_latitude': latitude,
                    'check_in_location_longitude': longitude,
                    'check_in_selfie': selfie,
                    'approval_status': Attendance.ApprovalStatus.PENDING,
                    'created_by': user
                }
            )
            
            # If record already exists, update check-in information
            if not created:
                attendance.attendance_status = Attendance.AttendanceStatus.PRESENT
                attendance.check_in_time = check_in_time
                attendance.check_in_location = location
                attendance.check_in_location_latitude = latitude
                attendance.check_in_location_longitude = longitude
                attendance.check_in_selfie = selfie
                attendance.approval_status = Attendance.ApprovalStatus.PENDING  # Reset to pending
                attendance.updated_by = user
                attendance.save()
            
            return attendance


class AttendancePunchOutSerializer(serializers.Serializer):
    time = serializers.DateTimeField(required=True, help_text='Check-out time (YYYY-MM-DD HH:MM:SS)')
    location = serializers.CharField(required=True, max_length=255, help_text='Check-out location name/address')
    latitude = serializers.DecimalField(required=True, max_digits=9, decimal_places=6, help_text='Check-out location latitude coordinate')
    longitude = serializers.DecimalField(required=True, max_digits=9, decimal_places=6, help_text='Check-out location longitude coordinate')
    
    def create(self, validated_data):
        """Update attendance record with punch-out data"""
        from django.db import transaction
        from datetime import date
        
        request = self.context['request']
        user = request.user
        
        # Get employee from user
        try:
            employee = Employee.objects.get(profile__user=user)
        except Employee.DoesNotExist:
            raise serializers.ValidationError({
                'employee': ['Employee record not found for this user. Please contact administrator.']
            })
        except Employee.MultipleObjectsReturned:
            employee = Employee.objects.filter(profile__user=user).first()
        
        check_out_time = validated_data.get('time')
        location = validated_data.get('location')
        latitude = validated_data.get('latitude')
        longitude = validated_data.get('longitude')
        attendance_date = check_out_time.date()
        
        with transaction.atomic():
            # Get existing attendance record for today
            try:
                attendance = Attendance.objects.get(
                    employee=employee,
                    attendance_date=attendance_date
                )
            except Attendance.DoesNotExist:
                raise serializers.ValidationError({
                    'attendance': ['No attendance record found for today. Please punch in first.']
                })
            
            # Update check-out information
            attendance.check_out_time = check_out_time
            attendance.check_out_location = location
            attendance.check_out_location_latitude = latitude
            attendance.check_out_location_longitude = longitude
            attendance.updated_by = user
            attendance.save()
            
            return attendance


# Payroll Serializers
class PayrollListSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    
    class Meta:
        model = PayrollRecord
        fields = [
            'id', 'employee', 'employee_name', 'employee_code', 'payroll_status',
            'period_from', 'period_to', 'working_days', 'days_present', 'net_amount',
            'payment_date', 'payment_mode', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_employee_name(self, obj):
        """Get employee name from profile user"""
        if obj.employee and obj.employee.profile and obj.employee.profile.user:
            user = obj.employee.profile.user
            full_name = f"{user.first_name} {user.last_name}".strip()
            return full_name if full_name else user.username
        return None


class PayrollDetailSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    
    class Meta:
        model = PayrollRecord
        fields = [
            'id', 'employee', 'employee_name', 'employee_code', 'payroll_status',
            'period_from', 'period_to', 'working_days', 'days_present', 'net_amount',
            'payment_date', 'payment_mode', 'bank_transaction_reference_number',
            'notes', 'created_at', 'updated_at', 'created_by', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def get_employee_name(self, obj):
        """Get employee name from profile user"""
        if obj.employee and obj.employee.profile and obj.employee.profile.user:
            user = obj.employee.profile.user
            full_name = f"{user.first_name} {user.last_name}".strip()
            return full_name if full_name else user.username
        return None


class PayrollCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollRecord
        fields = [
            'id', 'employee', 'payroll_status', 'period_from', 'period_to',
            'working_days', 'days_present', 'net_amount', 'payment_date',
            'payment_mode', 'bank_transaction_reference_number', 'notes'
        ]
        read_only_fields = ['id']
    
    def create(self, validated_data):
        """Create or update payroll record"""
        from django.db import transaction
        from datetime import date
        
        employee = validated_data.get('employee')
        period_from = validated_data.get('period_from')
        period_to = validated_data.get('period_to')
        
        # Extract month and year from period_from
        period_month = period_from.month
        period_year = period_from.year
        
        with transaction.atomic():
            # Check if payroll exists for this employee, month, and year
            existing_payroll = PayrollRecord.objects.filter(
                employee=employee,
                period_from__year=period_year,
                period_from__month=period_month
            ).first()
            
            if existing_payroll:
                # Update existing payroll
                existing_payroll.payroll_status = validated_data.get('payroll_status')
                existing_payroll.period_from = period_from
                existing_payroll.period_to = period_to
                existing_payroll.working_days = validated_data.get('working_days')
                existing_payroll.days_present = validated_data.get('days_present')
                existing_payroll.net_amount = validated_data.get('net_amount')
                existing_payroll.payment_date = validated_data.get('payment_date', None)
                existing_payroll.payment_mode = validated_data.get('payment_mode', None)
                existing_payroll.bank_transaction_reference_number = validated_data.get('bank_transaction_reference_number', None)
                existing_payroll.notes = validated_data.get('notes', None)
                user = self.context['request'].user
                existing_payroll.updated_by = user if user.is_authenticated else None
                existing_payroll.save()
                existing_payroll._was_updated = True
                return existing_payroll
            else:
                # Create new payroll
                user = self.context['request'].user
                validated_data['created_by'] = user if user.is_authenticated else None
                payroll = super().create(validated_data)
                payroll._was_updated = False
                return payroll


class PayrollMarkPaidSerializer(serializers.Serializer):
    payment_date = serializers.DateField(required=True, help_text='Payment date (YYYY-MM-DD)')
    payment_mode = serializers.ChoiceField(
        choices=PayrollRecord.PaymentMode.choices,
        required=True,
        help_text='Payment mode (Cash, Bank Transfer, Cheque, UPI)'
    )
    bank_transaction_reference_number = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=100,
        help_text='Bank transaction reference number (optional)'
    )


class BulkMarkPayrollPaidSerializer(serializers.Serializer):
    payroll_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text='List of payroll record IDs to mark as paid'
    )
    payment_date = serializers.DateField(required=True, help_text='Payment date (YYYY-MM-DD)')
    payment_mode = serializers.ChoiceField(
        choices=PayrollRecord.PaymentMode.choices,
        required=True,
        help_text='Payment mode (Cash, Bank Transfer, Cheque, UPI)'
    )
    bank_transaction_reference_number = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=100,
        help_text='Bank transaction reference number (optional)'
    )


class PayrollStatisticsSerializer(serializers.Serializer):
    total_payroll = serializers.DecimalField(max_digits=15, decimal_places=2)
    employees_count = serializers.IntegerField()
    total_payment_pending = serializers.IntegerField()
    total_payment_paid = serializers.IntegerField()


# Holiday Calendar Serializers
class HolidayCalendarListSerializer(serializers.ModelSerializer):
    """Serializer for listing holidays"""
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = HolidayCalander
        fields = [
            'id', 'name', 'date', 'type', 'type_display', 'created_at', 'created_by', 'created_by_username'
        ]
        read_only_fields = ['created_at', 'created_by']


class HolidayCalendarDetailSerializer(serializers.ModelSerializer):
    """Serializer for holiday details"""
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    updated_by_username = serializers.CharField(source='updated_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = HolidayCalander
        fields = [
            'id', 'name', 'date', 'type', 'type_display',
            'created_at', 'updated_at', 'created_by', 'created_by_username',
            'updated_by', 'updated_by_username'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']


class HolidayCalendarCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating holidays"""
    
    class Meta:
        model = HolidayCalander
        fields = [
            'id', 'name', 'date', 'type'
        ]
        read_only_fields = ['id']
    
    def create(self, validated_data):
        """Create holiday entry"""
        user = self.context['request'].user
        validated_data['created_by'] = user if user.is_authenticated else None
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Update holiday entry"""
        user = self.context['request'].user
        validated_data['updated_by'] = user if user.is_authenticated else None
        return super().update(instance, validated_data)


class HolidayCalendarStatisticsSerializer(serializers.Serializer):
    """Serializer for holiday calendar statistics"""
    total_holidays = serializers.IntegerField(help_text='Total holidays in current year')
    public_holidays = serializers.IntegerField(help_text='Public holidays (National) in current year')
    optional_holidays = serializers.IntegerField(help_text='Optional holidays (Festival) in current year')
