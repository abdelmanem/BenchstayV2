from django.urls import path, include

urlpatterns = [
    path('repairs/', include('hotelkit.repairs.urls')),
    path('api/', include('hotelkit.repairs.urls', namespace='api')),
    path('', include('hotelkit.guest_requests.urls', namespace='guest_requests')),
]
