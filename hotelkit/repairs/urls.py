from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ..views import (
    RepairRequestViewSet, RepairImportView, RepairTemplateView,
    RepairsDashboardView, repairs_import_view
)

# Create router for API endpoints
router = DefaultRouter()
router.register(r'repairs', RepairRequestViewSet, basename='repairs')

# API URL patterns
api_urlpatterns = [
    path('', include(router.urls)),
    path('repairs/import/', RepairImportView.as_view(), name='repairs-import'),
    path('repairs/template/', RepairTemplateView.as_view(), name='repairs-template'),
]

# Main URL patterns
urlpatterns = [
    path('api/', include(api_urlpatterns)),
    path('dashboard/', RepairsDashboardView.as_view(), name='repairs_dashboard'),
    path('import/', repairs_import_view, name='repairs_import'),
]
