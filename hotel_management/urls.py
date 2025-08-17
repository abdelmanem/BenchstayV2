from django.urls import path
from . import views
from . import views_api
from django.http import JsonResponse

app_name = 'hotel_management'

urlpatterns = [
    path('', views.home, name='home'),
        path('hotel-data/', views.hotel_competitor_management, name='hotel_data'),
    
    path('data-entry/', views.data_entry, name='data_entry'),
    path('api/hotel-data/<int:pk>/', views.hotel_data_api, name='hotel-data-api'),
    path('api/competitor-data/<int:pk>/', views.competitor_data_api, name='competitor-data-api'),
    path('api/ajax-metrics/', views.ajax_metrics, name='ajax_metrics'),
    path('api/revpar-matrix/', views_api.revpar_matrix_api, name='revpar-matrix-api'),
]