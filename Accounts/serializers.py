"""
Serializers for Accounts app.
"""
from rest_framework import serializers
from .models import PaymentTracker, BankAccount


class PaymentTrackerListSerializer(serializers.ModelSerializer):
    """Serializer for listing payment tracker records"""
    class Meta:
        model = PaymentTracker
        fields = [
            'id', 'worker_name', 'mobile_number', 'place_of_work',
            'net_salary', 'bank_name', 'account_number', 'ifsc_code',
            'payment_status', 'payment_date', 'payment_mode', 'sheet_period',
            'created_at'
        ]
        read_only_fields = ['created_at']


class PaymentTrackerDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed payment tracker record"""
    sheet_attachment_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentTracker
        fields = [
            'id', 'worker_name', 'mobile_number', 'place_of_work',
            'net_salary', 'bank_name', 'account_number', 'ifsc_code',
            'payment_status', 'payment_date', 'payment_mode',
            'sheet_period', 'sheet_attachment', 'sheet_attachment_url',
            'created_at', 'updated_at', 'created_by', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def get_sheet_attachment_url(self, obj):
        """Get sheet attachment URL"""
        if obj.sheet_attachment:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.sheet_attachment.url)
            return obj.sheet_attachment.url
        return None


class PaymentTrackerUploadSerializer(serializers.Serializer):
    """Serializer for uploading Excel sheet with payment data"""
    month = serializers.IntegerField(
        required=True,
        min_value=1,
        max_value=12,
        help_text='Month (1-12)'
    )
    year = serializers.IntegerField(
        required=True,
        min_value=2000,
        max_value=2100,
        help_text='Year (YYYY)'
    )
    excel_file = serializers.FileField(
        required=True,
        help_text='Excel file containing payment information with columns: Sr. No., Worker Name, Place Of Work, Mobile Number, Net Salary, Bank Name, Account Number, IFSC Code'
    )


class PaymentTrackerMarkPaidSerializer(serializers.Serializer):
    """Serializer for marking a payment tracker record as paid"""
    payment_date = serializers.DateField(
        required=True,
        help_text='Payment date (YYYY-MM-DD)'
    )
    payment_mode = serializers.ChoiceField(
        choices=PaymentTracker.PaymentMode.choices,
        required=True,
        help_text='Payment mode (Cash, Cheque, Bank Transfer, UPI)'
    )


class BulkMarkPaymentPaidSerializer(serializers.Serializer):
    """Serializer for bulk marking payment tracker records as paid"""
    payment_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text='List of payment tracker record IDs to mark as paid'
    )
    payment_date = serializers.DateField(
        required=True,
        help_text='Payment date (YYYY-MM-DD)'
    )
    payment_mode = serializers.ChoiceField(
        choices=PaymentTracker.PaymentMode.choices,
        required=True,
        help_text='Payment mode (Cash, Cheque, Bank Transfer, UPI)'
    )


class PaymentTrackerStatisticsSerializer(serializers.Serializer):
    """Serializer for payment tracking statistics"""
    total_payable = serializers.DecimalField(max_digits=15, decimal_places=2)
    pending_payment_count = serializers.IntegerField()
    pending_payment_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_paid = serializers.DecimalField(max_digits=15, decimal_places=2)


# Bank Account Serializers
class BankAccountListSerializer(serializers.ModelSerializer):
    """Serializer for listing bank accounts"""
    profile_id = serializers.IntegerField(source='profile.id', read_only=True)
    profile_name = serializers.SerializerMethodField()
    account_holder_name = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = BankAccount
        fields = [
            'id', 'profile_id', 'profile_name', 'account_holder_name',
            'bank_name', 'account_number', 'ifsc_code', 'branch',
            'created_at', 'created_by', 'created_by_username'
        ]
        read_only_fields = ['created_at', 'created_by']
    
    def get_profile_name(self, obj):
        """Get profile name from user"""
        if obj.profile and obj.profile.user:
            user = obj.profile.user
            if user.first_name or user.last_name:
                return f"{user.first_name or ''} {user.last_name or ''}".strip()
            return user.username
        return None
    
    def get_account_holder_name(self, obj):
        """Get account holder name from profile user"""
        if obj.profile and obj.profile.user:
            user = obj.profile.user
            if user.first_name or user.last_name:
                return f"{user.first_name or ''} {user.last_name or ''}".strip()
            return user.username
        return None


class BankAccountDetailSerializer(serializers.ModelSerializer):
    """Serializer for bank account details"""
    profile_id = serializers.IntegerField(source='profile.id', read_only=True)
    profile_name = serializers.SerializerMethodField()
    account_holder_name = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    updated_by_username = serializers.CharField(source='updated_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = BankAccount
        fields = [
            'id', 'profile_id', 'profile_name', 'account_holder_name',
            'bank_name', 'account_number', 'ifsc_code', 'branch',
            'created_at', 'updated_at', 'created_by', 'created_by_username',
            'updated_by', 'updated_by_username'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def get_profile_name(self, obj):
        """Get profile name from user"""
        if obj.profile and obj.profile.user:
            user = obj.profile.user
            if user.first_name or user.last_name:
                return f"{user.first_name or ''} {user.last_name or ''}".strip()
            return user.username
        return None
    
    def get_account_holder_name(self, obj):
        """Get account holder name from profile user"""
        if obj.profile and obj.profile.user:
            user = obj.profile.user
            if user.first_name or user.last_name:
                return f"{user.first_name or ''} {user.last_name or ''}".strip()
            return user.username
        return None


class BankAccountCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating bank accounts"""
    profile_id = serializers.IntegerField(write_only=True, required=True)
    
    class Meta:
        model = BankAccount
        fields = [
            'id', 'profile_id', 'bank_name', 'account_number', 'ifsc_code', 'branch'
        ]
        read_only_fields = ['id']
    
    def create(self, validated_data):
        """Create bank account"""
        from Profiles.models import Profile
        
        profile_id = validated_data.pop('profile_id')
        try:
            profile = Profile.objects.get(id=profile_id)
        except Profile.DoesNotExist:
            raise serializers.ValidationError({'profile_id': 'Profile not found'})
        
        validated_data['profile'] = profile
        user = self.context['request'].user
        validated_data['created_by'] = user if user.is_authenticated else None
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Update bank account"""
        if 'profile_id' in validated_data:
            from Profiles.models import Profile
            
            profile_id = validated_data.pop('profile_id')
            try:
                profile = Profile.objects.get(id=profile_id)
            except Profile.DoesNotExist:
                raise serializers.ValidationError({'profile_id': 'Profile not found'})
            
            validated_data['profile'] = profile
        
        user = self.context['request'].user
        validated_data['updated_by'] = user if user.is_authenticated else None
        return super().update(instance, validated_data)

