from django.urls import path
from . import views

app_name = "guest_experience"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("arrivals/", views.arrivals, name="arrivals"),
    path("arrivals/upload/", views.upload_arrivals, name="upload_arrivals"),
    path("arrivals/delete/", views.delete_arrivals, name="delete_arrivals"),
    path("arrivals/mark-in-house/", views.mark_in_house, name="mark_in_house"),
    path("in-house/", views.in_house, name="in_house"),
    path("departures/", views.departures, name="departures"),
    # API endpoints
    path("api/arrivals/", views.arrivals_api, name="arrivals_api"),
    path("api/in-house/", views.in_house_api, name="in_house_api"),
    path("api/departures/", views.departures_api, name="departures_api"),
]


