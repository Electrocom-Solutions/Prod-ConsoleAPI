from rest_framework import serializers
from .models import AMC, AMCBilling
from Clients.models import Client


class AMCBillingSerializer(serializers.ModelSerializer):
    period = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    payment_details = serializers.SerializerMethodField()
    
    class Meta:
        model = AMCBilling
        fields = [
            'id', 'bill_number', 'period', 'amount', 'status',
            'payment_details', 'bill_date', 'period_from', 'period_to',
            'paid', 'payment_date', 'payment_mode', 'notes'
        ]
        read_only_fields = ['id', 'bill_date', 'created_at', 'created_by']
    
    def get_period(self, obj):
        """Format period as 'From Date - To Date'"""
        return f"{obj.period_from} to {obj.period_to}"
    
    def get_status(self, obj):
        """Get payment status"""
        return "Paid" if obj.paid else "Pending"
    
    def get_payment_details(self, obj):
        """Get payment details"""
        if obj.paid:
            return {
                'payment_date': obj.payment_date,
                'payment_mode': obj.payment_mode
            }
        return None


class AMCListSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    client_id = serializers.IntegerField(source='client.id', read_only=True)
    days_until_expiry = serializers.SerializerMethodField()
    
    class Meta:
        model = AMC
        fields = [
            'id', 'amc_number', 'client', 'client_id', 'client_name',
            'amount', 'start_date', 'end_date', 'status', 'billing_cycle',
            'days_until_expiry', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_days_until_expiry(self, obj):
        """Calculate days until expiry"""
        from datetime import date
        today = date.today()
        if obj.end_date >= today:
            return (obj.end_date - today).days
        return None


class AMCDetailSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    client_id = serializers.IntegerField(source='client.id', read_only=True)
    billings = AMCBillingSerializer(many=True, read_only=True)
    total_amount = serializers.SerializerMethodField()
    paid_amount = serializers.SerializerMethodField()
    outstanding_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = AMC
        fields = [
            'id', 'amc_number', 'client', 'client_id', 'client_name',
            'amount', 'start_date', 'end_date', 'status', 'billing_cycle',
            'notes', 'total_amount', 'paid_amount', 'outstanding_amount',
            'billings', 'created_at', 'updated_at', 'created_by', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def get_total_amount(self, obj):
        """Calculate total amount from all billings"""
        from django.db.models import Sum
        total = obj.billings.aggregate(total=Sum('amount'))['total']
        return float(total) if total else 0.0
    
    def get_paid_amount(self, obj):
        """Calculate paid amount"""
        from django.db.models import Sum
        paid = obj.billings.filter(paid=True).aggregate(total=Sum('amount'))['total']
        return float(paid) if paid else 0.0
    
    def get_outstanding_amount(self, obj):
        """Calculate outstanding amount"""
        from django.db.models import Sum
        outstanding = obj.billings.filter(paid=False).aggregate(total=Sum('amount'))['total']
        return float(outstanding) if outstanding else 0.0


class AMCCreateSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all())
    
    class Meta:
        model = AMC
        fields = [
            'id', 'client', 'amc_number', 'amount', 'start_date', 'end_date',
            'billing_cycle', 'status', 'notes'
        ]
        read_only_fields = ['id']
    
    def validate_amc_number(self, value):
        """Validate AMC number uniqueness"""
        # Exclude current instance when updating
        queryset = AMC.objects.filter(amc_number=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("AMC number already exists.")
        return value
    
    def validate(self, data):
        """Validate dates"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError("End date must be after start date.")
        
        return data
    
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['created_by'] = user if user.is_authenticated else None
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        user = self.context['request'].user
        validated_data['updated_by'] = user if user.is_authenticated else None
        return super().update(instance, validated_data)


class AMCBillingDetailsSerializer(serializers.Serializer):
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    paid_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    outstanding_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    billings = AMCBillingSerializer(many=True)


class AMCStatisticsSerializer(serializers.Serializer):
    total_amcs = serializers.IntegerField()
    active_amcs = serializers.IntegerField()
    expiring_soon = serializers.IntegerField()
    pending_bills = serializers.IntegerField()


class AMCBillingUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating AMC billing payment status"""
    
    class Meta:
        model = AMCBilling
        fields = ['paid', 'payment_date', 'payment_mode', 'notes']
    
    def update(self, instance, validated_data):
        user = self.context['request'].user
        validated_data['updated_by'] = user if user.is_authenticated else None
        return super().update(instance, validated_data)

