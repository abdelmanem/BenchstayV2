from django.urls import path
from . import views

app_name = "guest_experience"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("dashboard/", views.dashboard, name="dashboard_detail"),
    path("arrivals/", views.arrivals, name="arrivals"),
    path("arrivals/upload/", views.upload_arrivals, name="upload_arrivals"),
    path("arrivals/edit/<str:confirmation_number>/", views.edit_arrival, name="edit_arrival"),
    path("arrivals/delete/", views.delete_arrivals, name="delete_arrivals"),
    path("arrivals/mark-in-house/", views.mark_in_house, name="mark_in_house"),
    path("in-house/", views.in_house, name="in_house"),
    path("in-house/mark-departed/", views.mark_departed, name="mark_departed"),
    path("in-house/update-room/", views.update_room, name="update_room"),
    path("courtesy-calls/", views.courtesy_calls, name="courtesy_calls"),
    path("courtesy-calls/dashboard/", views.courtesy_calls_dashboard, name="courtesy_calls_dashboard"),
    path("courtesy-calls/comments/", views.courtesy_comments, name="courtesy_comments"),
    path("departures/", views.departures, name="departures"),
    # API endpoints
    path("api/arrivals/", views.arrivals_api, name="arrivals_api"),
    path("api/in-house/", views.in_house_api, name="in_house_api"),
    path("api/departures/", views.departures_api, name="departures_api"),
    path("api/courtesy-calls/", views.courtesy_calls_api, name="courtesy_calls_api"),
    path("api/courtesy-calls/mark-done/", views.mark_courtesy_done, name="mark_courtesy_done"),
    path("api/dashboard/", views.dashboard_api, name="dashboard_api"),
]


