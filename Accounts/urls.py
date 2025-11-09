"""
URLs for Accounts app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentTrackerViewSet

router = DefaultRouter()
router.register(r'payment-tracker', PaymentTrackerViewSet, basename='payment-tracker')

urlpatterns = [
    path('', include(router.urls)),
]

