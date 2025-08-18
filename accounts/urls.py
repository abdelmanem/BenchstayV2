from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'accounts'

urlpatterns = [
    path('debug/', views.debug_info, name='debug'),
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('admin-settings/', views.admin_settings, name='admin_settings'),
    path('admin_settings/', views.admin_settings, name='admin_settings_alt'),
    path('help/', views.help_page, name='help'),
]