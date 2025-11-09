from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, TaskResourcesDashboardViewSet

router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'task-resources', TaskResourcesDashboardViewSet, basename='task-resources')

urlpatterns = [
    path('', include(router.urls)),
]

