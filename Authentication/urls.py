"""
Authentication URL Configuration
"""
from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    path('owner/login/', views.owner_login, name='owner_login'),
    path('employee/login/', views.employee_mobile_login, name='employee_mobile_login'),
    path('logout/', views.logout_view, name='logout'),
    path('user/', views.get_current_user, name='get_current_user'),
]

