"""
Views for Inventory app - Stock Dashboard.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Stock
from .serializers import (
    StockListSerializer,
    StockDetailSerializer,
    StockCreateSerializer,
    StockUpdateSerializer,
    StockStatisticsSerializer
)


class StockViewSet(viewsets.ModelViewSet):
    """
    Stock Dashboard APIs
    """
    queryset = Stock.objects.select_related('created_by', 'updated_by').all()
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return StockListSerializer
        elif self.action in ['retrieve']:
            return StockDetailSerializer
        elif self.action in ['create']:
            return StockCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return StockUpdateSerializer
        return StockListSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search by name
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset.order_by('-created_at')
    
    @swagger_auto_schema(
        operation_id='stock_list',
        operation_summary="List All Stock Items",
        operation_description="""
        Retrieve a list of all stock items with search functionality.
        
        **What it returns:**
        - List of stock items with basic information:
          * Resource Name (name)
          * Unit of Measure (unit_of_measure)
          * Stock Count (quantity)
          * Unit Price (price)
          * Description
          * Creation and update timestamps
        
        **Search Options:**
        - search: Search by stock item name (case-insensitive partial match)
        
        **Query Parameters:**
        - search (optional): Search by stock item name
        
        **Pagination:**
        Results are paginated (20 items per page by default) and sorted by creation date (newest first).
        """,
        tags=['Stock Dashboard'],
        manual_parameters=[
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description='Search by stock item name',
                type=openapi.TYPE_STRING,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of stock items",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'results': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT)
                        )
                    }
                )
            )
        }
    )
    def list(self, request, *args, **kwargs):
        """List all stock items with search"""
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='stock_statistics',
        operation_summary="Get Stock Management Statistics",
        operation_description="""
        Retrieve statistics for the stock management dashboard.
        
        **What it returns:**
        - total_resources: Total number of stock items in the inventory
        - total_inventory_value: Total value of all stock items (sum of quantity * price)
        - low_stock_items: Number of stock items with quantity below their min_threshold
        
        **Use Case:**
        Use this endpoint to populate dashboard tiles showing key metrics for stock management.
        """,
        tags=['Stock Dashboard'],
        responses={
            200: openapi.Response(
                description="Stock management statistics",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'total_resources': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total number of stock items'),
                        'total_inventory_value': openapi.Schema(type=openapi.TYPE_NUMBER, description='Total inventory value'),
                        'low_stock_items': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of low stock items (quantity < min_threshold)')
                    }
                )
            )
        }
    )
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """Get stock management statistics for dashboard"""
        # Total resources count
        total_resources = Stock.objects.count()
        
        # Calculate total inventory value (sum of quantity * price)
        # Using aggregation to calculate sum of (quantity * price)
        stocks = Stock.objects.all()
        total_inventory_value = 0
        low_stock_items = 0
        
        for stock in stocks:
            total_value = float(stock.quantity) * float(stock.price)
            total_inventory_value += total_value
            # Check if stock quantity is below the min_threshold
            # Only consider it low stock if min_threshold is set (> 0) and quantity is below it
            min_threshold_value = float(stock.min_threshold) if stock.min_threshold is not None else 0
            if min_threshold_value > 0 and float(stock.quantity) < min_threshold_value:
                low_stock_items += 1
        
        data = {
            'total_resources': total_resources,
            'total_inventory_value': float(total_inventory_value),
            'low_stock_items': low_stock_items
        }
        
        serializer = StockStatisticsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_id='stock_retrieve',
        operation_summary="Get Stock Item Details",
        operation_description="""
        Retrieve detailed information about a specific stock item.
        
        **What it returns:**
        - Complete stock item information including all fields
        - Created and updated by user information
        - Creation and update timestamps
        """,
        tags=['Stock Dashboard'],
        responses={
            200: StockDetailSerializer()
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """Get stock item details"""
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='stock_create',
        operation_summary="Add Stock Item",
        operation_description="""
        Add a new stock item to the inventory.
        
        **Required Fields:**
        - name: Resource Name
        - unit_of_measure: Unit of Measure (e.g., "kg", "pieces", "liters")
        - quantity: Stock Count (current quantity in stock)
        - price: Unit Price (price per unit)
        
        **Optional Fields:**
        - min_threshold: Minimum threshold for stock quantity (default: 0). If quantity falls below this value, the stock is considered 'low stock'.
        - description: Description of the stock item
        
        **Response:**
        Returns the created stock item with all details.
        """,
        tags=['Stock Dashboard'],
        responses={
            201: openapi.Response(
                description="Stock item created successfully",
                schema=StockCreateSerializer()
            ),
            400: openapi.Response(
                description="Invalid request data",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        }
    )
    def create(self, request, *args, **kwargs):
        """Add a new stock item"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @swagger_auto_schema(
        operation_id='stock_update',
        operation_summary="Edit Stock Item",
        operation_description="""
        Update an existing stock item. All fields are optional - only provided fields will be updated.
        
        **Fields:**
        - name: Resource Name
        - unit_of_measure: Unit of Measure
        - quantity: Stock Count
        - price: Unit Price
        - min_threshold: Minimum threshold for stock quantity
        - description: Description
        
        **Response:**
        Returns the updated stock item with all details.
        """,
        tags=['Stock Dashboard'],
        responses={
            200: openapi.Response(
                description="Stock item updated successfully",
                schema=StockUpdateSerializer()
            ),
            404: openapi.Response(description="Stock item not found")
        }
    )
    def update(self, request, *args, **kwargs):
        """Update stock item information"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_id='stock_partial_update',
        operation_summary="Partial Update Stock Item",
        operation_description="""
        Partially update a stock item. Only provided fields will be updated.
        
        **Use Case:**
        Use this endpoint when you only want to update specific fields without affecting others.
        """,
        tags=['Stock Dashboard'],
        responses={
            200: openapi.Response(
                description="Stock item partially updated successfully",
                schema=StockUpdateSerializer()
            )
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """Partially update stock item information"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='stock_delete',
        operation_summary="Delete Stock Item",
        operation_description="""
        Delete a stock item from the inventory. This action is permanent and cannot be undone.
        
        **Warning:**
        Deleting a stock item will permanently remove it from the system.
        
        **Use Case:**
        Use this endpoint when you need to permanently remove a stock item from the inventory.
        """,
        tags=['Stock Dashboard'],
        responses={
            204: openapi.Response(description="Stock item deleted successfully"),
            404: openapi.Response(description="Stock item not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        """Delete a stock item"""
        return super().destroy(request, *args, **kwargs)
