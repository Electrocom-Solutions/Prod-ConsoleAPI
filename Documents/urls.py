from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentTemplateViewSet

router = DefaultRouter()
router.register(r'templates', DocumentTemplateViewSet, basename='documentmanagement')

urlpatterns = [
    path('', include(router.urls)),
]

