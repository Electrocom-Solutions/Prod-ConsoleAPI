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

