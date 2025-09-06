from django.urls import path, include

urlpatterns = [
    path('repairs/', include('hotelkit.repairs.urls')),
]
