from rest_framework import serializers
from django.db.models import Sum, Q
from django.db import transaction
from .models import Tender, TenderDeposit, TenderDocument
from Analytics.models import ActivityLog


class TenderDepositSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderDeposit
        fields = [
            'id', 'dd_date', 'dd_number', 'dd_amount', 'dd_beneficiary_name',
            'bank_name', 'deposit_type', 'is_refunded', 'refund_date'
        ]
        read_only_fields = ['id', 'created_at', 'created_by']


class TenderListSerializer(serializers.ModelSerializer):
    total_emd_cost = serializers.SerializerMethodField()
    security_deposit_1 = serializers.SerializerMethodField()
    security_deposit_2 = serializers.SerializerMethodField()
    pending_emd_amount = serializers.SerializerMethodField()
    has_pending_emd = serializers.SerializerMethodField()
    
    class Meta:
        model = Tender
        fields = [
            'id', 'name', 'reference_number', 'filed_date', 'start_date',
            'end_date', 'estimated_value', 'status', 'emd_collected',
            'emd_collected_date', 'total_emd_cost',
            'security_deposit_1', 'security_deposit_2', 'pending_emd_amount',
            'has_pending_emd', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_total_emd_cost(self, obj):
        """Calculate total EMD cost (Security Deposit 1 + Security Deposit 2)"""
        total = obj.deposits.aggregate(
            total=Sum('dd_amount')
        )['total']
        return float(total) if total else 0.0
    
    def get_security_deposit_1(self, obj):
        """Get Security Deposit 1 amount"""
        deposit = obj.deposits.filter(deposit_type=TenderDeposit.DepositType.EMD_SECURITY1).first()
        return float(deposit.dd_amount) if deposit else 0.0
    
    def get_security_deposit_2(self, obj):
        """Get Security Deposit 2 amount"""
        deposit = obj.deposits.filter(deposit_type=TenderDeposit.DepositType.EMD_SECURITY2).first()
        return float(deposit.dd_amount) if deposit else 0.0
    
    def get_pending_emd_amount(self, obj):
        """Calculate pending EMD amount based on tender status (only if not collected)"""
        if obj.emd_collected:
            return 0.0
        if obj.status == Tender.Status.CLOSED:
            # Closed: collect whole EMD (Security Deposit 1 + Security Deposit 2)
            return self.get_total_emd_cost(obj)
        elif obj.status == Tender.Status.LOST:
            # Lost: collect only Security Deposit 1
            return self.get_security_deposit_1(obj)
        return 0.0
    
    def get_has_pending_emd(self, obj):
        """Check if tender has pending EMD (Lost/Closed status and EMD not collected)"""
        return obj.status in [Tender.Status.CLOSED, Tender.Status.LOST] and not obj.emd_collected


class TenderDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = TenderDocument
        fields = [
            'id', 'file', 'file_url', 'file_name', 'created_at', 'created_by', 'created_by_username'
        ]
        read_only_fields = ['id', 'created_at', 'created_by']
    
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None
    
    def get_file_name(self, obj):
        if obj.file:
            return obj.file.name.split('/')[-1]
        return None


class ActivityFeedSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = ActivityLog
        fields = [
            'id', 'entity_type', 'entity_id', 'action', 'description',
            'created_at', 'created_by', 'created_by_username'
        ]
        read_only_fields = ['id', 'entity_type', 'entity_id', 'action', 'description', 'created_at', 'created_by']


class TenderDetailSerializer(serializers.ModelSerializer):
    deposits = TenderDepositSerializer(many=True, read_only=True)
    documents = TenderDocumentSerializer(many=True, read_only=True)
    total_emd_cost = serializers.SerializerMethodField()
    security_deposit_1 = serializers.SerializerMethodField()
    security_deposit_2 = serializers.SerializerMethodField()
    pending_emd_amount = serializers.SerializerMethodField()
    activity_feed = serializers.SerializerMethodField()
    
    class Meta:
        model = Tender
        fields = [
            'id', 'name', 'reference_number', 'description', 'filed_date',
            'start_date', 'end_date', 'estimated_value', 'status',
            'emd_collected', 'emd_collected_date', 'emd_collected_by',
            'total_emd_cost', 'security_deposit_1', 'security_deposit_2',
            'pending_emd_amount', 'deposits', 'documents', 'activity_feed',
            'created_at', 'updated_at', 'created_by', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by', 'emd_collected_by']
    
    def get_total_emd_cost(self, obj):
        """Calculate total EMD cost"""
        total = obj.deposits.aggregate(total=Sum('dd_amount'))['total']
        return float(total) if total else 0.0
    
    def get_security_deposit_1(self, obj):
        """Get Security Deposit 1 amount"""
        deposit = obj.deposits.filter(deposit_type=TenderDeposit.DepositType.EMD_SECURITY1).first()
        return float(deposit.dd_amount) if deposit else 0.0
    
    def get_security_deposit_2(self, obj):
        """Get Security Deposit 2 amount"""
        deposit = obj.deposits.filter(deposit_type=TenderDeposit.DepositType.EMD_SECURITY2).first()
        return float(deposit.dd_amount) if deposit else 0.0
    
    def get_pending_emd_amount(self, obj):
        """Calculate pending EMD amount (only if not collected)"""
        if obj.emd_collected:
            return 0.0
        if obj.status == Tender.Status.CLOSED:
            return self.get_total_emd_cost(obj)
        elif obj.status == Tender.Status.LOST:
            return self.get_security_deposit_1(obj)
        return 0.0
    
    def get_activity_feed(self, obj):
        """Get activity feed for this tender"""
        activities = ActivityLog.objects.filter(
            entity_type=ActivityLog.EntityType.TENDER,
            entity_id=obj.id
        ).select_related('created_by').order_by('-created_at')
        return ActivityFeedSerializer(activities, many=True, context=self.context).data


class TenderDepositCreateSerializer(serializers.Serializer):
    """Nested serializer for creating deposits"""
    dd_date = serializers.DateField()
    dd_number = serializers.CharField(max_length=100)
    dd_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    dd_bank_name = serializers.CharField(max_length=255)
    dd_beneficiary_name = serializers.CharField(max_length=255)


class TenderCreateSerializer(serializers.ModelSerializer):
    # Security Deposit 1 fields
    security_deposit_1_dd_date = serializers.DateField(required=False, allow_null=True)
    security_deposit_1_dd_number = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    security_deposit_1_dd_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    security_deposit_1_dd_bank_name = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    security_deposit_1_dd_beneficiary_name = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    
    # Security Deposit 2 fields
    security_deposit_2_dd_date = serializers.DateField(required=False, allow_null=True)
    security_deposit_2_dd_number = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    security_deposit_2_dd_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    security_deposit_2_dd_bank_name = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    security_deposit_2_dd_beneficiary_name = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    class Meta:
        model = Tender
        fields = [
            'id', 'name', 'reference_number', 'description', 'filed_date',
            'start_date', 'end_date', 'estimated_value', 'status',
            'security_deposit_1_dd_date', 'security_deposit_1_dd_number',
            'security_deposit_1_dd_amount', 'security_deposit_1_dd_bank_name',
            'security_deposit_1_dd_beneficiary_name',
            'security_deposit_2_dd_date', 'security_deposit_2_dd_number',
            'security_deposit_2_dd_amount', 'security_deposit_2_dd_bank_name',
            'security_deposit_2_dd_beneficiary_name'
        ]
        read_only_fields = ['id']
    
    def create(self, validated_data):
        # Extract deposit data
        security_deposit_1_data = {
            'dd_date': validated_data.pop('security_deposit_1_dd_date', None),
            'dd_number': validated_data.pop('security_deposit_1_dd_number', None),
            'dd_amount': validated_data.pop('security_deposit_1_dd_amount', None),
            'dd_bank_name': validated_data.pop('security_deposit_1_dd_bank_name', None),
            'dd_beneficiary_name': validated_data.pop('security_deposit_1_dd_beneficiary_name', None),
        }
        
        security_deposit_2_data = {
            'dd_date': validated_data.pop('security_deposit_2_dd_date', None),
            'dd_number': validated_data.pop('security_deposit_2_dd_number', None),
            'dd_amount': validated_data.pop('security_deposit_2_dd_amount', None),
            'dd_bank_name': validated_data.pop('security_deposit_2_dd_bank_name', None),
            'dd_beneficiary_name': validated_data.pop('security_deposit_2_dd_beneficiary_name', None),
        }
        
        user = self.context['request'].user
        validated_data['created_by'] = user if user.is_authenticated else None
        
        with transaction.atomic():
            # Create tender
            tender = super().create(validated_data)
            
            # Create Security Deposit 1 if provided
            if security_deposit_1_data.get('dd_number') and security_deposit_1_data.get('dd_amount'):
                TenderDeposit.objects.create(
                    tender=tender,
                    deposit_type=TenderDeposit.DepositType.EMD_SECURITY1,
                    dd_date=security_deposit_1_data['dd_date'],
                    dd_number=security_deposit_1_data['dd_number'],
                    dd_amount=security_deposit_1_data['dd_amount'],
                    bank_name=security_deposit_1_data['dd_bank_name'],
                    dd_beneficiary_name=security_deposit_1_data['dd_beneficiary_name'],
                    created_by=user if user.is_authenticated else None
                )
            
            # Create Security Deposit 2 if provided
            if security_deposit_2_data.get('dd_number') and security_deposit_2_data.get('dd_amount'):
                TenderDeposit.objects.create(
                    tender=tender,
                    deposit_type=TenderDeposit.DepositType.EMD_SECURITY2,
                    dd_date=security_deposit_2_data['dd_date'],
                    dd_number=security_deposit_2_data['dd_number'],
                    dd_amount=security_deposit_2_data['dd_amount'],
                    bank_name=security_deposit_2_data['dd_bank_name'],
                    dd_beneficiary_name=security_deposit_2_data['dd_beneficiary_name'],
                    created_by=user if user.is_authenticated else None
                )
            
            # Create activity log
            ActivityLog.objects.create(
                entity_type=ActivityLog.EntityType.TENDER,
                entity_id=tender.id,
                action=ActivityLog.Action.CREATED,
                description=f"Tender {tender.name} created",
                created_by=user if user.is_authenticated else None
            )
        
        return tender
    
    def update(self, instance, validated_data):
        # Extract deposit data
        security_deposit_1_data = {
            'dd_date': validated_data.pop('security_deposit_1_dd_date', None),
            'dd_number': validated_data.pop('security_deposit_1_dd_number', None),
            'dd_amount': validated_data.pop('security_deposit_1_dd_amount', None),
            'dd_bank_name': validated_data.pop('security_deposit_1_dd_bank_name', None),
            'dd_beneficiary_name': validated_data.pop('security_deposit_1_dd_beneficiary_name', None),
        }
        
        security_deposit_2_data = {
            'dd_date': validated_data.pop('security_deposit_2_dd_date', None),
            'dd_number': validated_data.pop('security_deposit_2_dd_number', None),
            'dd_amount': validated_data.pop('security_deposit_2_dd_amount', None),
            'dd_bank_name': validated_data.pop('security_deposit_2_dd_bank_name', None),
            'dd_beneficiary_name': validated_data.pop('security_deposit_2_dd_beneficiary_name', None),
        }
        
        user = self.context['request'].user
        validated_data['updated_by'] = user if user.is_authenticated else None
        
        with transaction.atomic():
            # Update tender
            tender = super().update(instance, validated_data)
            
            # Update or create Security Deposit 1
            if any(security_deposit_1_data.values()):
                deposit1, created = TenderDeposit.objects.get_or_create(
                    tender=tender,
                    deposit_type=TenderDeposit.DepositType.EMD_SECURITY1,
                    defaults={
                        'dd_date': security_deposit_1_data.get('dd_date'),
                        'dd_number': security_deposit_1_data.get('dd_number', ''),
                        'dd_amount': security_deposit_1_data.get('dd_amount', 0),
                        'bank_name': security_deposit_1_data.get('dd_bank_name', ''),
                        'dd_beneficiary_name': security_deposit_1_data.get('dd_beneficiary_name', ''),
                        'created_by': self.context['request'].user
                    }
                )
                if not created:
                    if security_deposit_1_data.get('dd_date') is not None:
                        deposit1.dd_date = security_deposit_1_data['dd_date']
                    if security_deposit_1_data.get('dd_number') is not None:
                        deposit1.dd_number = security_deposit_1_data['dd_number']
                    if security_deposit_1_data.get('dd_amount') is not None:
                        deposit1.dd_amount = security_deposit_1_data['dd_amount']
                    if security_deposit_1_data.get('dd_bank_name') is not None:
                        deposit1.bank_name = security_deposit_1_data['dd_bank_name']
                    if security_deposit_1_data.get('dd_beneficiary_name') is not None:
                        deposit1.dd_beneficiary_name = security_deposit_1_data['dd_beneficiary_name']
                    deposit1.updated_by = self.context['request'].user
                    deposit1.save()
            
            # Update or create Security Deposit 2
            if any(security_deposit_2_data.values()):
                deposit2, created = TenderDeposit.objects.get_or_create(
                    tender=tender,
                    deposit_type=TenderDeposit.DepositType.EMD_SECURITY2,
                    defaults={
                        'dd_date': security_deposit_2_data.get('dd_date'),
                        'dd_number': security_deposit_2_data.get('dd_number', ''),
                        'dd_amount': security_deposit_2_data.get('dd_amount', 0),
                        'bank_name': security_deposit_2_data.get('dd_bank_name', ''),
                        'dd_beneficiary_name': security_deposit_2_data.get('dd_beneficiary_name', ''),
                        'created_by': self.context['request'].user
                    }
                )
                if not created:
                    if security_deposit_2_data.get('dd_date') is not None:
                        deposit2.dd_date = security_deposit_2_data['dd_date']
                    if security_deposit_2_data.get('dd_number') is not None:
                        deposit2.dd_number = security_deposit_2_data['dd_number']
                    if security_deposit_2_data.get('dd_amount') is not None:
                        deposit2.dd_amount = security_deposit_2_data['dd_amount']
                    if security_deposit_2_data.get('dd_bank_name') is not None:
                        deposit2.bank_name = security_deposit_2_data['dd_bank_name']
                    if security_deposit_2_data.get('dd_beneficiary_name') is not None:
                        deposit2.dd_beneficiary_name = security_deposit_2_data['dd_beneficiary_name']
                    deposit2.updated_by = self.context['request'].user
                    deposit2.save()
            
            # Create activity log
            ActivityLog.objects.create(
                entity_type=ActivityLog.EntityType.TENDER,
                entity_id=tender.id,
                action=ActivityLog.Action.UPDATED,
                description=f"Tender {tender.name} updated",
                created_by=self.context['request'].user
            )
        
        return tender


class TenderDocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class TenderStatisticsSerializer(serializers.Serializer):
    total_tenders = serializers.IntegerField()
    tenders_filed = serializers.IntegerField()
    tenders_awarded = serializers.IntegerField()
    total_value_awarded = serializers.DecimalField(max_digits=15, decimal_places=2)
    pending_emds = serializers.IntegerField()
    pending_emd_amount = serializers.DecimalField(max_digits=15, decimal_places=2)

