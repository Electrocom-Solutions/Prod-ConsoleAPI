from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmployeeViewSet, ContractWorkerViewSet, AttendanceViewSet, PayrollViewSet, HolidayCalendarViewSet

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'contract-workers', ContractWorkerViewSet, basename='contract-worker')
router.register(r'attendance', AttendanceViewSet, basename='attendance')
router.register(r'payroll', PayrollViewSet, basename='payroll')
router.register(r'holidays', HolidayCalendarViewSet, basename='holiday')

urlpatterns = [
    path('', include(router.urls)),
]

