"""
Authentication URL Configuration
"""
from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    path('owner/login/', views.owner_login, name='owner_login'),
    path('employee/login/', views.employee_mobile_login, name='employee_mobile_login'),
    path('employee/forgot-password/', views.employee_forgot_password, name='employee_forgot_password'),
    path('employee/verify-otp/', views.employee_verify_otp, name='employee_verify_otp'),
    path('employee/reset-password/', views.employee_reset_password, name='employee_reset_password'),
    path('logout/', views.logout_view, name='logout'),
    path('user/', views.get_current_user, name='get_current_user'),
]

