from django.urls import path
from .views import (
    UploadView, DashboardView,
    ByDepartmentReportView, ByPriorityReportView,
    DelayedReportView, MonthlySummaryReportView,
)

app_name = 'guest_requests'

urlpatterns = [
    path('guest-requests/upload/', UploadView.as_view(), name='upload'),
    path('guest-requests/dashboard/', DashboardView.as_view(), name='dashboard'),
    path('guest-requests/reports/by-department/', ByDepartmentReportView.as_view(), name='by_department'),
    path('guest-requests/reports/by-priority/', ByPriorityReportView.as_view(), name='by_priority'),
    path('guest-requests/reports/delayed/', DelayedReportView.as_view(), name='delayed'),
    path('guest-requests/reports/monthly-summary/', MonthlySummaryReportView.as_view(), name='monthly_summary'),
]


