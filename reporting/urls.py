from django.urls import path
from . import views
from . import cache_utils
from . import ajax_views
from . import views_performance

app_name = 'reporting'

urlpatterns = [
    path('', views.report_dashboard, name='dashboard'),
    path('revenue-reports/', views.revenue_reports, name='revenue_reports'),
    path('occupancy-reports/', views.occupancy_reports, name='occupancy_reports'),
    path('competitor-analysis/', views.competitor_analysis, name='competitor_analysis'),
    path('competitor-advanced-analytics/', views.competitor_advanced_analytics, name='competitor_advanced_analytics'),
    path('export-pdf/', views.export_competitor_analytics_pdf, name='export_competitor_analytics_pdf'),
    # AJAX endpoints
    path('ajax/refresh-competitor-analytics/', ajax_views.refresh_competitor_analytics, name='refresh_competitor_analytics'),
    path('clear-cache/', cache_utils.clear_cache, name='clear_cache'),
    path('export-competitor-analytics/', views.export_competitor_analytics, name='export_competitor_analytics'),
    path('hotel-performance/<int:hotel_id>/', views_performance.hotel_performance_report, name='hotel_performance'),
    path('export-pdf/<int:hotel_id>/', views.export_competitor_analytics_pdf, name='export_competitor_analytics_pdf'),
    path('hotel-performance/', views_performance.hotel_performance_report, name='hotel_performance_default'),

]