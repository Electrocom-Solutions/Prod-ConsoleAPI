from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Client, Firm
from AMC.models import AMC
from Profiles.models import Profile


class ClientListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    phone_number = serializers.CharField(read_only=True)
    has_active_amc = serializers.SerializerMethodField()
    
    class Meta:
        model = Client
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email', 'phone_number',
            'has_active_amc', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_has_active_amc(self, obj):
        """Check if client has active AMC"""
        return obj.amcs.filter(status=AMC.Status.ACTIVE).exists()


class ClientDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    photo_url = serializers.SerializerMethodField()
    aadhar_card_url = serializers.SerializerMethodField()
    pan_card_url = serializers.SerializerMethodField()
    email = serializers.EmailField()
    phone_number = serializers.CharField()
    
    class Meta:
        model = Client
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email', 'phone_number',
            'photo', 'photo_url', 'date_of_birth', 'gender', 'aadhar_number', 'pan_number',
            'aadhar_card_url', 'pan_card_url', 'designation', 'joining_date', 'monthly_salary', 'notes',
            'profile', 'created_at', 'updated_at', 'created_by', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def get_photo_url(self, obj):
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None
    
    def get_aadhar_card_url(self, obj):
        """Get Aadhar card URL from profile"""
        if obj.profile and obj.profile.aadhar_card:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile.aadhar_card.url)
            return obj.profile.aadhar_card.url
        return None
    
    def get_pan_card_url(self, obj):
        """Get PAN card URL from profile"""
        if obj.profile and obj.profile.pan_card:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile.pan_card.url)
            return obj.profile.pan_card.url
        return None


class ClientCreateUpdateSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    photo_url = serializers.SerializerMethodField()
    aadhar_card_url = serializers.SerializerMethodField()
    pan_card_url = serializers.SerializerMethodField()
    profile = serializers.PrimaryKeyRelatedField(queryset=Profile.objects.all(), required=False, allow_null=True)
    
    # File upload fields for Aadhar and PAN cards
    aadhar_card = serializers.FileField(write_only=True, required=False, allow_null=True)
    pan_card = serializers.FileField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Client
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email', 'phone_number',
            'photo', 'photo_url', 'date_of_birth', 'gender', 'aadhar_number', 'pan_number',
            'aadhar_card', 'pan_card', 'aadhar_card_url', 'pan_card_url',
            'designation', 'joining_date', 'monthly_salary', 'notes', 'profile'
        ]
        read_only_fields = ['id']
    
    def get_photo_url(self, obj):
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None
    
    def get_aadhar_card_url(self, obj):
        """Get Aadhar card URL from profile"""
        if obj.profile and obj.profile.aadhar_card:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile.aadhar_card.url)
            return obj.profile.aadhar_card.url
        return None
    
    def get_pan_card_url(self, obj):
        """Get PAN card URL from profile"""
        if obj.profile and obj.profile.pan_card:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile.pan_card.url)
            return obj.profile.pan_card.url
        return None
    
    def create(self, validated_data):
        from django.db import transaction
        
        # Extract file uploads
        aadhar_card = validated_data.pop('aadhar_card', None)
        pan_card = validated_data.pop('pan_card', None)
        
        # Extract date_of_birth and gender from validated_data as they belong to Profile
        date_of_birth = validated_data.pop('date_of_birth', None)
        gender = validated_data.pop('gender', None)
        
        # Create or get profile for the client
        profile = validated_data.pop('profile', None)
        
        with transaction.atomic():
            if not profile:
                # Create a new user and profile if not provided
                email = validated_data.get('email', '')
                phone = validated_data.get('phone_number', '')
                username = email or f"client_{phone}" or f"client_{Client.objects.count() + 1}"
                
                # Make username unique
                base_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{counter}"
                    counter += 1
                
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=validated_data.get('first_name', ''),
                    last_name=validated_data.get('last_name', '')
                )
                
                # Create profile for the user with file uploads
                profile = Profile.objects.create(
                    user=user,
                    aadhar_card=aadhar_card,
                    pan_card=pan_card,
                    date_of_birth=date_of_birth,
                    gender=gender,
                    created_by=self.context['request'].user
                )
            else:
                # Update existing profile with file uploads if provided
                if aadhar_card is not None:
                    profile.aadhar_card = aadhar_card
                if pan_card is not None:
                    profile.pan_card = pan_card
                if date_of_birth is not None:
                    profile.date_of_birth = date_of_birth
                if gender is not None:
                    profile.gender = gender
                user = self.context['request'].user
                profile.updated_by = user if user.is_authenticated else None
                profile.save()
            
            user = self.context['request'].user
            validated_data['profile'] = profile
            validated_data['created_by'] = user if user.is_authenticated else None
            return super().create(validated_data)
    
    def update(self, instance, validated_data):
        from django.db import transaction
        
        # Extract file uploads
        aadhar_card = validated_data.pop('aadhar_card', None)
        pan_card = validated_data.pop('pan_card', None)
        
        # Extract date_of_birth and gender from validated_data as they belong to Profile
        date_of_birth = validated_data.pop('date_of_birth', None)
        gender = validated_data.pop('gender', None)
        
        user = self.context['request'].user
        validated_data['updated_by'] = user if user.is_authenticated else None
        
        with transaction.atomic():
            # Update profile user info if provided
            profile = validated_data.pop('profile', None)
            if profile and instance.profile and instance.profile.user:
                user = instance.profile.user
                if validated_data.get('email'):
                    user.email = validated_data.get('email', user.email)
                if validated_data.get('first_name'):
                    user.first_name = validated_data.get('first_name', user.first_name)
                if validated_data.get('last_name'):
                    user.last_name = validated_data.get('last_name', user.last_name)
                user.save()
            
            # Update profile with file uploads if provided
            if instance.profile:
                profile_obj = instance.profile
                if aadhar_card is not None:
                    profile_obj.aadhar_card = aadhar_card
                if pan_card is not None:
                    profile_obj.pan_card = pan_card
                if date_of_birth is not None:
                    profile_obj.date_of_birth = date_of_birth
                if gender is not None:
                    profile_obj.gender = gender
                user = self.context['request'].user
                profile_obj.updated_by = user if user.is_authenticated else None
                profile_obj.save()
            
            return super().update(instance, validated_data)


class ClientStatisticsSerializer(serializers.Serializer):
    total_clients = serializers.IntegerField()
    active_amcs_count = serializers.IntegerField()
    open_projects_count = serializers.IntegerField()
    outstanding_amount = serializers.DecimalField(max_digits=15, decimal_places=2)


# Firm Serializers
class FirmListSerializer(serializers.ModelSerializer):
    """Serializer for listing firms"""
    type_display = serializers.CharField(source='get_firm_type_display', read_only=True)
    firm_owner_name = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = Firm
        fields = [
            'id', 'firm_name', 'firm_type', 'type_display', 'firm_owner_profile',
            'firm_owner_name', 'official_email', 'official_mobile_number',
            'address', 'gst_number', 'pan_number', 'created_at', 'created_by', 'created_by_username'
        ]
        read_only_fields = ['created_at', 'created_by']
    
    def get_firm_owner_name(self, obj):
        """Get firm owner name from profile user"""
        if obj.firm_owner_profile and obj.firm_owner_profile.user:
            user = obj.firm_owner_profile.user
            full_name = f"{user.first_name} {user.last_name}".strip()
            return full_name if full_name else user.username
        return None


class FirmDetailSerializer(serializers.ModelSerializer):
    """Serializer for firm details"""
    type_display = serializers.CharField(source='get_firm_type_display', read_only=True)
    firm_owner_name = serializers.SerializerMethodField()
    firm_owner_email = serializers.SerializerMethodField()
    firm_owner_phone = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    updated_by_username = serializers.CharField(source='updated_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = Firm
        fields = [
            'id', 'firm_name', 'firm_type', 'type_display', 'firm_owner_profile',
            'firm_owner_name', 'firm_owner_email', 'firm_owner_phone',
            'official_email', 'official_mobile_number', 'address',
            'gst_number', 'pan_number',
            'created_at', 'updated_at', 'created_by', 'created_by_username',
            'updated_by', 'updated_by_username'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def get_firm_owner_name(self, obj):
        """Get firm owner name from profile user"""
        if obj.firm_owner_profile and obj.firm_owner_profile.user:
            user = obj.firm_owner_profile.user
            full_name = f"{user.first_name} {user.last_name}".strip()
            return full_name if full_name else user.username
        return None
    
    def get_firm_owner_email(self, obj):
        """Get firm owner email from profile user"""
        if obj.firm_owner_profile and obj.firm_owner_profile.user:
            return obj.firm_owner_profile.user.email
        return None
    
    def get_firm_owner_phone(self, obj):
        """Get firm owner phone from profile"""
        # Phone might be stored in Profile model, adjust based on your Profile model
        return None


class FirmCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating firms"""
    firm_owner_profile = serializers.PrimaryKeyRelatedField(
        queryset=Profile.objects.all(),
        required=False,
        allow_null=True,
        help_text='Firm Owner Profile (dropdown)'
    )
    
    class Meta:
        model = Firm
        fields = [
            'id', 'firm_name', 'firm_type', 'firm_owner_profile',
            'official_email', 'official_mobile_number', 'address',
            'gst_number', 'pan_number'
        ]
        read_only_fields = ['id']
    
    def create(self, validated_data):
        """Create firm entry"""
        user = self.context['request'].user
        validated_data['created_by'] = user if user.is_authenticated else None
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Update firm entry"""
        user = self.context['request'].user
        validated_data['updated_by'] = user if user.is_authenticated else None
        return super().update(instance, validated_data)

