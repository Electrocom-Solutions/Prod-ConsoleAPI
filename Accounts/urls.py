"""
URLs for Accounts app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentTrackerViewSet, BankAccountViewSet

router = DefaultRouter()
router.register(r'payment-tracker', PaymentTrackerViewSet, basename='payment-tracker')
router.register(r'bank-accounts', BankAccountViewSet, basename='bank-account')

urlpatterns = [
    path('', include(router.urls)),
]

