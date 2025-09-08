from django.urls import path
from .views import (
    UploadView, DashboardView,
    ByDepartmentReportView, ByPriorityReportView,
    DelayedReportView, MonthlySummaryReportView,
    SLAComplianceReportView, RequestsHeatmapReportView,
    TopFrequentReportView, DepartmentPerformanceReportView,
    GuestRequestsByTypeView, GuestRequestDetailView, GuestRequestEditView, GuestRequestDeleteView,
)

app_name = 'guest_requests'

urlpatterns = [
    path('guest-requests/upload/', UploadView.as_view(), name='upload'),
    path('guest-requests/dashboard/', DashboardView.as_view(), name='dashboard'),
    path('guest-requests/reports/by-department/', ByDepartmentReportView.as_view(), name='by_department'),
    path('guest-requests/reports/by-priority/', ByPriorityReportView.as_view(), name='by_priority'),
    path('guest-requests/reports/delayed/', DelayedReportView.as_view(), name='delayed'),
    path('guest-requests/reports/monthly-summary/', MonthlySummaryReportView.as_view(), name='monthly_summary'),
    path('guest-requests/reports/sla-compliance/', SLAComplianceReportView.as_view(), name='sla_compliance'),
    path('guest-requests/reports/heatmap/', RequestsHeatmapReportView.as_view(), name='heatmap'),
    path('guest-requests/reports/top-frequent/', TopFrequentReportView.as_view(), name='top_frequent'),
    path('guest-requests/reports/department-performance/', DepartmentPerformanceReportView.as_view(), name='department_performance'),
    path('guest-requests/by-type/', GuestRequestsByTypeView.as_view(), name='by_type'),
    path('guest-requests/<int:pk>/', GuestRequestDetailView.as_view(), name='guest_request_detail'),
    path('guest-requests/<int:pk>/edit/', GuestRequestEditView.as_view(), name='guest_request_edit'),
    path('guest-requests/<int:pk>/delete/', GuestRequestDeleteView.as_view(), name='guest_request_delete'),
]


