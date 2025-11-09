from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AMCViewSet

router = DefaultRouter()
router.register(r'amcs', AMCViewSet, basename='amc')

urlpatterns = [
    path('', include(router.urls)),
]

