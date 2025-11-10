from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
from .models import Profile, MobileNumber


class CurrentUserProfileSerializer(serializers.ModelSerializer):
    """Serializer for current user's profile details"""
    photo_url = serializers.SerializerMethodField()
    aadhar_card_url = serializers.SerializerMethodField()
    pan_card_url = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    
    class Meta:
        model = Profile
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'photo', 'photo_url', 'date_of_birth', 'gender',
            'address', 'city', 'state', 'pin_code', 'country',
            'aadhar_number', 'pan_number',
            'aadhar_card', 'aadhar_card_url',
            'pan_card', 'pan_card_url',
            'phone_number',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_photo_url(self, obj):
        """Get photo URL"""
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None
    
    def get_aadhar_card_url(self, obj):
        """Get Aadhar card URL"""
        if obj.aadhar_card:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.aadhar_card.url)
            return obj.aadhar_card.url
        return None
    
    def get_pan_card_url(self, obj):
        """Get PAN card URL"""
        if obj.pan_card:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pan_card.url)
            return obj.pan_card.url
        return None
    
    def get_phone_number(self, obj):
        """Get primary phone number"""
        try:
            mobile = MobileNumber.objects.filter(user=obj.user, is_primary=True).first()
            if mobile:
                return mobile.mobile_number
            # If no primary, get first mobile number
            mobile = MobileNumber.objects.filter(user=obj.user).first()
            if mobile:
                return mobile.mobile_number
        except:
            pass
        return None


class CurrentUserProfileUpdateSerializer(serializers.Serializer):
    """Serializer for updating current user's profile"""
    # User fields
    username = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    
    # Profile fields
    photo = serializers.ImageField(required=False, allow_null=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.CharField(max_length=20, required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    state = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    pin_code = serializers.CharField(max_length=20, required=False, allow_null=True, allow_blank=True)
    country = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    aadhar_number = serializers.CharField(max_length=20, required=False, allow_null=True, allow_blank=True)
    pan_number = serializers.CharField(max_length=20, required=False, allow_null=True, allow_blank=True)
    aadhar_card = serializers.FileField(required=False, allow_null=True)
    pan_card = serializers.FileField(required=False, allow_null=True)
    
    # Phone number
    phone_number = serializers.CharField(max_length=20, required=False, allow_null=True, allow_blank=True)
    
    # Password change
    current_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    new_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    confirm_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    def validate(self, attrs):
        """Validate password change"""
        current_password = attrs.get('current_password', '')
        new_password = attrs.get('new_password', '')
        confirm_password = attrs.get('confirm_password', '')
        
        # If any password field is provided, all must be provided
        if current_password or new_password or confirm_password:
            if not current_password or not new_password or not confirm_password:
                raise serializers.ValidationError({
                    'error': 'All password fields are required to change password.'
                })
            
            if new_password != confirm_password:
                raise serializers.ValidationError({
                    'error': 'New password and confirm password do not match.'
                })
            
            if len(new_password) < 6:
                raise serializers.ValidationError({
                    'error': 'New password must be at least 6 characters long.'
                })
            
            # Verify current password
            user = self.context['request'].user
            if not user.check_password(current_password):
                raise serializers.ValidationError({
                    'error': 'Current password is incorrect.'
                })
        
        # Validate username uniqueness (if changing)
        username = attrs.get('username')
        if username:
            user = self.context['request'].user
            if User.objects.filter(username=username).exclude(id=user.id).exists():
                raise serializers.ValidationError({
                    'username': 'Username already exists.'
                })
        
        # Validate email uniqueness (if changing)
        email = attrs.get('email')
        if email:
            user = self.context['request'].user
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                raise serializers.ValidationError({
                    'email': 'Email already exists.'
                })
        
        return attrs
    
    def update(self, instance, validated_data):
        """Update user and profile"""
        user = instance.user
        request = self.context['request']
        
        # Update User fields
        if 'username' in validated_data:
            user.username = validated_data['username']
        if 'email' in validated_data:
            user.email = validated_data['email']
        if 'first_name' in validated_data:
            user.first_name = validated_data['first_name']
        if 'last_name' in validated_data:
            user.last_name = validated_data['last_name']
        
        # Update password if provided
        if 'new_password' in validated_data and validated_data['new_password']:
            user.set_password(validated_data['new_password'])
            # Update session to prevent logout after password change
            update_session_auth_hash(request, user)
        
        user.save()
        
        # Update Profile fields
        profile_fields = [
            'photo', 'date_of_birth', 'gender', 'address', 'city',
            'state', 'pin_code', 'country', 'aadhar_number', 'pan_number',
            'aadhar_card', 'pan_card'
        ]
        
        for field in profile_fields:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        
        # Update updated_by
        instance.updated_by = user
        instance.save()
        
        # Update phone number
        phone_number = validated_data.get('phone_number')
        if phone_number:
            # Get or create primary mobile number
            mobile, created = MobileNumber.objects.get_or_create(
                user=user,
                is_primary=True,
                defaults={
                    'mobile_number': phone_number,
                    'is_primary': True,
                    'created_by': user,
                    'updated_by': user
                }
            )
            if not created:
                # Update existing primary mobile number
                mobile.mobile_number = phone_number
                mobile.updated_by = user
                mobile.save()
            else:
                # If this is a new primary, unset other primaries
                MobileNumber.objects.filter(
                    user=user,
                    is_primary=True
                ).exclude(id=mobile.id).update(is_primary=False)
        
        return instance


class ProfileCreateSerializer(serializers.Serializer):
    """Serializer for creating a new profile with user"""
    # User fields
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=False, allow_blank=True, default='')
    email = serializers.EmailField(required=True)
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    
    # Profile fields
    photo = serializers.ImageField(required=False, allow_null=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.CharField(max_length=20, required=False, allow_null=True, allow_blank=True)
    address = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    state = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    pin_code = serializers.CharField(max_length=20, required=False, allow_null=True, allow_blank=True)
    country = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    aadhar_number = serializers.CharField(max_length=20, required=False, allow_null=True, allow_blank=True)
    pan_number = serializers.CharField(max_length=20, required=False, allow_null=True, allow_blank=True)
    aadhar_card = serializers.FileField(required=False, allow_null=True)
    pan_card = serializers.FileField(required=False, allow_null=True)
    
    def validate_email(self, value):
        """Validate email uniqueness"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def create(self, validated_data):
        """Create user and profile"""
        from django.db import transaction
        from django.contrib.auth.models import User
        
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name', '')
        email = validated_data.pop('email')
        phone_number = validated_data.pop('phone_number', None)
        
        # Extract profile fields
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
        
        request_user = self.context['request'].user
        
        with transaction.atomic():
            # Create user
            username = email or f"profile_{Profile.objects.count() + 1}"
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
            
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name or ''
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
            
            # Create primary mobile number if provided
            if phone_number:
                MobileNumber.objects.create(
                    user=user,
                    mobile_number=phone_number,
                    is_primary=True,
                    created_by=request_user if request_user.is_authenticated else None,
                    updated_by=request_user if request_user.is_authenticated else None
                )
            
            return profile


class ProfileListSerializer(serializers.ModelSerializer):
    """Serializer for listing profiles"""
    full_name = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Profile
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_first_name(self, obj):
        """Get first name from user"""
        if obj.user:
            return obj.user.first_name or ""
        return ""
    
    def get_last_name(self, obj):
        """Get last name from user"""
        if obj.user:
            return obj.user.last_name or ""
        return ""
    
    def get_full_name(self, obj):
        """Get full name from user"""
        if obj.user:
            first_name = obj.user.first_name or ""
            last_name = obj.user.last_name or ""
            full_name = f"{first_name} {last_name}".strip()
            if full_name:
                return full_name
            return obj.user.username or ""
        return ""
    
    def get_email(self, obj):
        """Get email from user"""
        if obj.user:
            return obj.user.email or ""
        return ""
    
    def get_phone_number(self, obj):
        """Get primary phone number"""
        try:
            mobile = MobileNumber.objects.filter(user=obj.user, is_primary=True).first()
            if mobile:
                return mobile.mobile_number
            # If no primary, get first mobile number
            mobile = MobileNumber.objects.filter(user=obj.user).first()
            if mobile:
                return mobile.mobile_number
        except:
            pass
        return None

