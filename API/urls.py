"""
URL configuration for API project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger/OpenAPI Schema View
schema_view = get_schema_view(
   openapi.Info(
      title="Electrocom API",
      default_version='v1',
      description="""
# Electrocom API Documentation

This API provides comprehensive endpoints for managing the Electrocom application.

## Core Modules
- **Dashboard**: Analytics and statistics endpoints
- **Client Management**: Client CRUD operations and management
- **Settings Module**: Firm management and system configuration

## Business Modules
- **AMC Management**: Annual Maintenance Contract management
- **Tender Management**: Tender processing and EMD tracking
- **Project Management**: Project lifecycle management
- **Task Management**: Task creation, tracking, and approval
- **Task Resources Dashboard**: Resource usage tracking and costing

## HR & Payroll Modules
- **Employee Management**: Employee CRUD and management
- **Contract Worker Management**: Contract worker management
- **Attendance Management**: Attendance tracking and approval
- **Payroll Management**: Payroll processing and payment tracking
- **Holiday Calendar Dashboard**: Holiday calendar management

## Financial Modules
- **Payment Tracking**: Payment tracker for contract workers

## Document & Communication Modules
- **Document Management**: Document template management
- **Notifications**: In-app notifications management
- **Email Template Dashboard**: Email template management and sending

## Inventory Module
- **Stock Dashboard**: Stock/inventory management

## Authentication
Most endpoints require authentication. Use Basic Authentication or Bearer Token authentication.

## Pagination
All list endpoints are paginated with 20 items per page by default.
      """,
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@electrocom.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
   patterns=[
       path('api/', include('Analytics.urls')),
       path('api/', include('Authentication.urls')),
       path('api/documents/', include('Documents.urls')),
       path('api/', include('Clients.urls')),
       path('api/', include('AMC.urls')),
       path('api/', include('Tenders.urls')),
       path('api/', include('Projects.urls')),
       path('api/', include('Tasks.urls')),
       path('api/', include('HR.urls')),
       path('api/', include('Accounts.urls')),
       path('api/', include('Inventory.urls')),
       path('api/', include('Notifications.urls')),
   ],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API URLs
    path('api/', include('Analytics.urls')),
    path('api/', include('Authentication.urls')),
    path('api/documents/', include('Documents.urls')),
    path('api/', include('Clients.urls')),
    path('api/', include('AMC.urls')),
    path('api/', include('Tenders.urls')),
    path('api/', include('Projects.urls')),
    path('api/', include('Tasks.urls')),
    path('api/', include('HR.urls')),
    path('api/', include('Accounts.urls')),
    path('api/', include('Inventory.urls')),
    path('api/', include('Notifications.urls')),
    
    # Swagger/OpenAPI Documentation
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
