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

