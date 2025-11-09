"""
Serializers for Inventory app - Stock Dashboard.
"""
from rest_framework import serializers
from .models import Stock


class StockListSerializer(serializers.ModelSerializer):
    """Serializer for listing stock items"""
    class Meta:
        model = Stock
        fields = [
            'id', 'name', 'unit_of_measure', 'quantity', 'price',
            'description', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class StockDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed stock item"""
    class Meta:
        model = Stock
        fields = [
            'id', 'name', 'unit_of_measure', 'quantity', 'price',
            'description', 'created_at', 'updated_at',
            'created_by', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']


class StockCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a stock item"""
    class Meta:
        model = Stock
        fields = [
            'id', 'name', 'unit_of_measure', 'quantity', 'price', 'description'
        ]
        read_only_fields = ['id']
    
    def create(self, validated_data):
        """Create a new stock item"""
        user = self.context['request'].user
        validated_data['created_by'] = user if user.is_authenticated else None
        return super().create(validated_data)


class StockUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a stock item"""
    class Meta:
        model = Stock
        fields = [
            'id', 'name', 'unit_of_measure', 'quantity', 'price', 'description'
        ]
        read_only_fields = ['id']
    
    def update(self, instance, validated_data):
        """Update a stock item"""
        user = self.context['request'].user
        validated_data['updated_by'] = user if user.is_authenticated else None
        return super().update(instance, validated_data)


class StockStatisticsSerializer(serializers.Serializer):
    """Serializer for stock statistics"""
    total_resources = serializers.IntegerField()
    total_inventory_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    low_stock_items = serializers.IntegerField()

