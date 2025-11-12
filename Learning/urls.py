from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TrainingVideoViewSet

router = DefaultRouter()
router.register(r'training-videos', TrainingVideoViewSet, basename='training-video')

urlpatterns = [
    path('', include(router.urls)),
]

