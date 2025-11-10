from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Client, Firm
from AMC.models import AMC
from Profiles.models import Profile


class ClientListSerializer(serializers.ModelSerializer):
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    phone_number = serializers.CharField(read_only=True)
    has_active_amc = serializers.SerializerMethodField()
    
    class Meta:
        model = Client
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email', 'phone_number',
            'has_active_amc', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_first_name(self, obj):
        """Get first name from profile.user"""
        if obj.profile and obj.profile.user:
            return obj.profile.user.first_name or ""
        return ""
    
    def get_last_name(self, obj):
        """Get last name from profile.user"""
        if obj.profile and obj.profile.user:
            return obj.profile.user.last_name or ""
        return ""
    
    def get_full_name(self, obj):
        """Get full name from profile.user"""
        if obj.profile and obj.profile.user:
            first_name = obj.profile.user.first_name or ""
            last_name = obj.profile.user.last_name or ""
            full_name = f"{first_name} {last_name}".strip()
            if full_name:
                return full_name
            # Fallback to username if name is empty
            if obj.profile.user.username:
                return obj.profile.user.username
        return ""
    
    def get_email(self, obj):
        """Get email from profile.user"""
        if obj.profile and obj.profile.user:
            return obj.profile.user.email or ""
        return ""
    
    def get_has_active_amc(self, obj):
        """Check if client has active AMC"""
        return obj.amcs.filter(status=AMC.Status.ACTIVE).exists()


class ClientDetailSerializer(serializers.ModelSerializer):
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    phone_number = serializers.CharField(read_only=True)
    photo_url = serializers.SerializerMethodField()
    aadhar_card_url = serializers.SerializerMethodField()
    pan_card_url = serializers.SerializerMethodField()
    # Address fields from Profile model
    address = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    pin_code = serializers.SerializerMethodField()
    country = serializers.SerializerMethodField()
    
    class Meta:
        model = Client
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email', 'phone_number',
            'photo', 'photo_url', 'date_of_birth', 'gender', 'aadhar_number', 'pan_number',
            'aadhar_card_url', 'pan_card_url', 'primary_contact_name', 'notes',
            'profile', 'address', 'city', 'state', 'pin_code', 'country',
            'created_at', 'updated_at', 'created_by', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def get_first_name(self, obj):
        """Get first name from profile.user"""
        if obj.profile and obj.profile.user:
            return obj.profile.user.first_name or ""
        return ""
    
    def get_last_name(self, obj):
        """Get last name from profile.user"""
        if obj.profile and obj.profile.user:
            return obj.profile.user.last_name or ""
        return ""
    
    def get_full_name(self, obj):
        """Get full name from profile.user"""
        if obj.profile and obj.profile.user:
            first_name = obj.profile.user.first_name or ""
            last_name = obj.profile.user.last_name or ""
            full_name = f"{first_name} {last_name}".strip()
            if full_name:
                return full_name
            # Fallback to username if name is empty
            if obj.profile.user.username:
                return obj.profile.user.username
        return ""
    
    def get_email(self, obj):
        """Get email from profile.user"""
        if obj.profile and obj.profile.user:
            return obj.profile.user.email or ""
        return ""
    
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


class ClientCreateUpdateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(write_only=True, required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    photo_url = serializers.SerializerMethodField()
    aadhar_card_url = serializers.SerializerMethodField()
    pan_card_url = serializers.SerializerMethodField()
    profile = serializers.PrimaryKeyRelatedField(queryset=Profile.objects.all(), required=False, allow_null=True)
    
    # File upload fields for Aadhar and PAN cards
    aadhar_card = serializers.FileField(write_only=True, required=False, allow_null=True)
    pan_card = serializers.FileField(write_only=True, required=False, allow_null=True)
    
    # Address fields (stored in Profile model)
    address = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)
    city = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)
    state = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)
    pin_code = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)
    country = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)
    
    class Meta:
        model = Client
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email', 'phone_number',
            'photo', 'photo_url', 'date_of_birth', 'gender', 'aadhar_number', 'pan_number',
            'aadhar_card', 'pan_card', 'aadhar_card_url', 'pan_card_url',
            'notes', 'profile', 'primary_contact_name', 'address', 'city', 'state', 'pin_code', 'country'
        ]
        read_only_fields = ['id']
    
    def get_full_name(self, obj):
        """Get full name from profile.user"""
        if obj.profile and obj.profile.user:
            first_name = obj.profile.user.first_name or ""
            last_name = obj.profile.user.last_name or ""
            full_name = f"{first_name} {last_name}".strip()
            if full_name:
                return full_name
            # Fallback to username if name is empty
            if obj.profile.user.username:
                return obj.profile.user.username
        return ""
    
    def get_email(self, obj):
        """Get email from profile.user"""
        if obj.profile and obj.profile.user:
            return obj.profile.user.email or ""
        return ""
    
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
        
        # Extract user fields (first_name, last_name, email)
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        email = validated_data.pop('email', '')
        
        # Extract file uploads
        aadhar_card = validated_data.pop('aadhar_card', None)
        pan_card = validated_data.pop('pan_card', None)
        
        # Extract date_of_birth and gender from validated_data as they belong to Profile
        date_of_birth = validated_data.pop('date_of_birth', None)
        gender = validated_data.pop('gender', None)
        
        # Extract address fields from validated_data as they belong to Profile
        address = validated_data.pop('address', None)
        city = validated_data.pop('city', None)
        state = validated_data.pop('state', None)
        pin_code = validated_data.pop('pin_code', None)
        country = validated_data.pop('country', None)
        
        # Create or get profile for the client
        profile = validated_data.pop('profile', None)
        
        with transaction.atomic():
            if not profile:
                # Create a new user and profile if not provided
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
                    first_name=first_name or '',
                    last_name=last_name or ''
                )
                
                # Create profile for the user with file uploads and address
                profile = Profile.objects.create(
                    user=user,
                    aadhar_card=aadhar_card,
                    pan_card=pan_card,
                    date_of_birth=date_of_birth,
                    gender=gender,
                    address=address,
                    city=city,
                    state=state,
                    pin_code=pin_code,
                    country=country,
                    created_by=self.context['request'].user
                )
            else:
                # Update existing profile's user and profile fields if provided
                if profile and profile.user:
                    if first_name:
                        profile.user.first_name = first_name
                    if last_name:
                        profile.user.last_name = last_name
                    if email:
                        profile.user.email = email
                    profile.user.save()
                
                # Update existing profile with file uploads and address if provided
                if aadhar_card is not None:
                    profile.aadhar_card = aadhar_card
                if pan_card is not None:
                    profile.pan_card = pan_card
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
                user = self.context['request'].user
                profile.updated_by = user if user.is_authenticated else None
                profile.save()
            
            user = self.context['request'].user
            validated_data['profile'] = profile
            validated_data['created_by'] = user if user.is_authenticated else None
            return super().create(validated_data)
    
    def update(self, instance, validated_data):
        from django.db import transaction
        
        # CRITICAL: Check if user fields were provided BEFORE popping
        # This allows us to distinguish between "field not sent" (not in dict) and "field sent as empty" (empty string)
        first_name_provided = 'first_name' in validated_data
        last_name_provided = 'last_name' in validated_data
        email_provided = 'email' in validated_data
        
        # Extract user fields (first_name, last_name, email)
        first_name = validated_data.pop('first_name', None)
        last_name = validated_data.pop('last_name', None)
        email = validated_data.pop('email', None)
        
        # Extract file uploads
        aadhar_card = validated_data.pop('aadhar_card', None)
        pan_card = validated_data.pop('pan_card', None)
        
        # Extract date_of_birth and gender from validated_data as they belong to Profile
        date_of_birth = validated_data.pop('date_of_birth', None)
        gender = validated_data.pop('gender', None)
        
        # CRITICAL: Check if address fields were provided BEFORE popping
        # This allows us to distinguish between "field not sent" (not in dict) and "field sent as empty" (empty string)
        address_provided = 'address' in validated_data
        city_provided = 'city' in validated_data
        state_provided = 'state' in validated_data
        pin_code_provided = 'pin_code' in validated_data
        country_provided = 'country' in validated_data
        primary_contact_name_provided = 'primary_contact_name' in validated_data
        
        # Extract address fields from validated_data as they belong to Profile
        address = validated_data.pop('address', None)
        city = validated_data.pop('city', None)
        state = validated_data.pop('state', None)
        pin_code = validated_data.pop('pin_code', None)
        country = validated_data.pop('country', None)
        primary_contact_name = validated_data.pop('primary_contact_name', None)
        
        user = self.context['request'].user
        validated_data['updated_by'] = user if user.is_authenticated else None
        
        with transaction.atomic():
            # Update profile user info if provided
            # CRITICAL: Update first_name and last_name even if empty strings to allow clearing them
            if instance.profile and instance.profile.user:
                user_obj = instance.profile.user
                if first_name_provided:
                    user_obj.first_name = first_name if first_name is not None else ''
                if last_name_provided:
                    user_obj.last_name = last_name if last_name is not None else ''
                if email_provided:
                    user_obj.email = email if email is not None else ''
                user_obj.save()
            
            # Update profile with file uploads and address if provided
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
                # CRITICAL: Update address fields if they were provided (even if empty strings)
                # This allows clearing fields by sending empty strings
                if address_provided:
                    profile_obj.address = address if address is not None else ''
                if city_provided:
                    profile_obj.city = city if city is not None else ''
                if state_provided:
                    profile_obj.state = state if state is not None else ''
                if pin_code_provided:
                    profile_obj.pin_code = pin_code if pin_code is not None else ''
                if country_provided:
                    profile_obj.country = country if country is not None else ''
                user = self.context['request'].user
                profile_obj.updated_by = user if user.is_authenticated else None
                profile_obj.save()
            
            # CRITICAL: Update primary_contact_name on Client model if provided
            # This field is on the Client model, not Profile
            if primary_contact_name_provided:
                instance.primary_contact_name = primary_contact_name if primary_contact_name is not None else ''
            
            # CRITICAL: Update phone_number on Client model if provided
            # This field is on the Client model, not Profile
            if 'phone_number' in validated_data:
                phone_number = validated_data.get('phone_number')
                instance.phone_number = phone_number if phone_number is not None else ''
            
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

