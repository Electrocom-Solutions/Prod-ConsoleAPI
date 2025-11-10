"""
Profile URL Configuration
"""
from django.urls import path
from . import views

app_name = 'profiles'

urlpatterns = [
    path('profiles/', views.list_profiles, name='list_profiles'),
    path('profile/', views.get_current_user_profile, name='get_current_user_profile'),
    path('profile/update/', views.update_current_user_profile, name='update_current_user_profile'),
    path('profile/create/', views.create_profile, name='create_profile'),
]

