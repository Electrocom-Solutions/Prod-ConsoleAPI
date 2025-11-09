from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClientViewSet, FirmViewSet

router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'firms', FirmViewSet, basename='firm')

urlpatterns = [
    path('', include(router.urls)),
]

