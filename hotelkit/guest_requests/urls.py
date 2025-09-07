from django.urls import path
from .views import UploadView, DashboardView

app_name = 'guest_requests'

urlpatterns = [
    path('guest-requests/upload/', UploadView.as_view(), name='upload'),
    path('guest-requests/dashboard/', DashboardView.as_view(), name='dashboard'),
]


