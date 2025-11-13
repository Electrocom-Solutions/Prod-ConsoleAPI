"""
Authentication Serializers
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from Profiles.models import MobileNumber


class OwnerLoginSerializer(serializers.Serializer):
    """
    Serializer for owner login
    Supports login with email, username, or mobile number
    """
    login_identifier = serializers.CharField(
        required=True,
        help_text="Email, username, or mobile number"
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text="User password"
    )
    remember_me = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Remember me checkbox - extends session expiry if checked"
    )
    
    def validate(self, attrs):
        login_identifier = attrs.get('login_identifier')
        password = attrs.get('password')
        
        if not login_identifier or not password:
            raise serializers.ValidationError({
                'error': 'Both login identifier and password are required.'
            })
        
        user = None
        
        # Try to find user by email
        try:
            user = User.objects.get(email=login_identifier)
        except User.DoesNotExist:
            pass
        
        # If not found by email, try username
        if not user:
            try:
                user = User.objects.get(username=login_identifier)
            except User.DoesNotExist:
                pass
        
        # If still not found, try mobile number
        if not user:
            try:
                mobile = MobileNumber.objects.get(mobile_number=login_identifier)
                user = mobile.user
            except MobileNumber.DoesNotExist:
                pass
        
        if not user:
            raise serializers.ValidationError({
                'error': 'Invalid login credentials. User not found.'
            })
        
        # Authenticate user
        user = authenticate(username=user.username, password=password)
        
        if not user:
            raise serializers.ValidationError({
                'error': 'Invalid login credentials. Incorrect password.'
            })
        
        if not user.is_active:
            raise serializers.ValidationError({
                'error': 'User account is disabled.'
            })
        
        # Check if user is staff or superuser (required for web app access)
        if not (user.is_staff or user.is_superuser):
            raise serializers.ValidationError({
                'error': 'Access denied. Only staff members and superusers can access the web application.'
            })
        
        attrs['user'] = user
        return attrs


class EmployeeMobileLoginSerializer(serializers.Serializer):
    """
    Serializer for employee mobile app login
    Supports login with mobile number and password only
    """
    mobile_number = serializers.CharField(
        required=True,
        help_text="Mobile number"
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text="User password"
    )
    
    def validate(self, attrs):
        mobile_number = attrs.get('mobile_number')
        password = attrs.get('password')
        
        if not mobile_number or not password:
            raise serializers.ValidationError({
                'error': 'Both mobile number and password are required.'
            })
        
        # Find user by mobile number
        try:
            mobile = MobileNumber.objects.get(mobile_number=mobile_number)
            user = mobile.user
        except MobileNumber.DoesNotExist:
            raise serializers.ValidationError({
                'error': 'Invalid login credentials. Mobile number not found.'
            })
        
        # Authenticate user
        user = authenticate(username=user.username, password=password)
        
        if not user:
            raise serializers.ValidationError({
                'error': 'Invalid login credentials. Incorrect password.'
            })
        
        if not user.is_active:
            raise serializers.ValidationError({
                'error': 'User account is disabled.'
            })
        
        # Check if user has an employee profile
        from HR.models import Employee
        try:
            employee = Employee.objects.get(profile__user=user)
        except Employee.DoesNotExist:
            raise serializers.ValidationError({
                'error': 'Access denied. Employee record not found for this user.'
            })
        
        attrs['user'] = user
        attrs['employee'] = employee
        return attrs


class EmployeeForgotPasswordSerializer(serializers.Serializer):
    """
    Serializer for employee forgot password request
    Validates mobile number and checks if it belongs to an employee
    """
    mobile_number = serializers.CharField(
        required=True,
        help_text="Mobile number"
    )
    
    def validate(self, attrs):
        mobile_number = attrs.get('mobile_number')
        
        if not mobile_number:
            raise serializers.ValidationError({
                'error': 'Mobile number is required.'
            })
        
        # Find user by mobile number
        try:
            mobile = MobileNumber.objects.get(mobile_number=mobile_number)
            user = mobile.user
        except MobileNumber.DoesNotExist:
            # Don't reveal if mobile number exists for security
            # Return success message anyway
            return attrs
        
        if not user.is_active:
            # Don't reveal if account is disabled for security
            return attrs
        
        # Check if user has an employee profile
        from HR.models import Employee
        try:
            employee = Employee.objects.get(profile__user=user)
            attrs['user'] = user
            attrs['employee'] = employee
        except Employee.DoesNotExist:
            # Don't reveal if employee record exists for security
            pass
        
        return attrs


class EmployeeVerifyOTPSerializer(serializers.Serializer):
    """
    Serializer for verifying OTP code for password reset
    """
    mobile_number = serializers.CharField(
        required=True,
        help_text="Mobile number"
    )
    otp = serializers.CharField(
        required=True,
        max_length=6,
        min_length=6,
        help_text="6-digit OTP code"
    )
    
    def validate(self, attrs):
        mobile_number = attrs.get('mobile_number')
        otp = attrs.get('otp')
        
        if not mobile_number or not otp:
            raise serializers.ValidationError({
                'error': 'Both mobile number and OTP are required.'
            })
        
        # Find user by mobile number
        try:
            mobile = MobileNumber.objects.get(mobile_number=mobile_number)
            user = mobile.user
        except MobileNumber.DoesNotExist:
            raise serializers.ValidationError({
                'error': 'Invalid mobile number.'
            })
        
        # Check if user has an employee profile
        from HR.models import Employee
        try:
            employee = Employee.objects.get(profile__user=user)
        except Employee.DoesNotExist:
            raise serializers.ValidationError({
                'error': 'Access denied. Employee record not found.'
            })
        
        # Find OTP record
        from Profiles.models import OTP
        from django.utils import timezone
        from datetime import timedelta
        
        otp_record = OTP.objects.filter(
            user=user,
            otp=otp,
            otp_type=OTP.OTPType.E,
            otp_for=OTP.OTPFor.RESET,
            is_verified=False
        ).order_by('-created_at').first()
        
        if not otp_record:
            raise serializers.ValidationError({
                'error': 'Invalid or expired OTP code.'
            })
        
        # Check if OTP is expired (10 minutes)
        if otp_record.created_at < timezone.now() - timedelta(minutes=10):
            raise serializers.ValidationError({
                'error': 'OTP code has expired. Please request a new one.'
            })
        
        attrs['user'] = user
        attrs['employee'] = employee
        attrs['otp_record'] = otp_record
        
        return attrs


class EmployeeResetPasswordSerializer(serializers.Serializer):
    """
    Serializer for resetting employee password
    """
    mobile_number = serializers.CharField(
        required=True,
        help_text="Mobile number"
    )
    otp = serializers.CharField(
        required=True,
        max_length=6,
        min_length=6,
        help_text="6-digit OTP code"
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        min_length=8,
        help_text="New password (minimum 8 characters)"
    )
    confirm_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text="Confirm new password"
    )
    
    def validate(self, attrs):
        mobile_number = attrs.get('mobile_number')
        otp = attrs.get('otp')
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')
        
        if not mobile_number or not otp or not new_password or not confirm_password:
            raise serializers.ValidationError({
                'error': 'All fields are required.'
            })
        
        # Validate password match
        if new_password != confirm_password:
            raise serializers.ValidationError({
                'error': 'Passwords do not match.'
            })
        
        # Validate password length
        if len(new_password) < 8:
            raise serializers.ValidationError({
                'error': 'Password must be at least 8 characters long.'
            })
        
        # Find user by mobile number
        try:
            mobile = MobileNumber.objects.get(mobile_number=mobile_number)
            user = mobile.user
        except MobileNumber.DoesNotExist:
            raise serializers.ValidationError({
                'error': 'Invalid mobile number.'
            })
        
        # Check if user has an employee profile
        from HR.models import Employee
        try:
            employee = Employee.objects.get(profile__user=user)
        except Employee.DoesNotExist:
            raise serializers.ValidationError({
                'error': 'Access denied. Employee record not found.'
            })
        
        # Find and verify OTP record
        from Profiles.models import OTP
        from django.utils import timezone
        from datetime import timedelta
        
        otp_record = OTP.objects.filter(
            user=user,
            otp=otp,
            otp_type=OTP.OTPType.E,
            otp_for=OTP.OTPFor.RESET
        ).order_by('-created_at').first()
        
        if not otp_record:
            raise serializers.ValidationError({
                'error': 'Invalid or expired OTP code.'
            })
        
        # Check if OTP is verified
        if not otp_record.is_verified:
            raise serializers.ValidationError({
                'error': 'OTP code not verified. Please verify the OTP first.'
            })
        
        # Check if OTP is expired (10 minutes)
        if otp_record.created_at < timezone.now() - timedelta(minutes=10):
            raise serializers.ValidationError({
                'error': 'OTP code has expired. Please request a new one.'
            })
        
        attrs['user'] = user
        attrs['employee'] = employee
        attrs['otp_record'] = otp_record
        
        return attrs

