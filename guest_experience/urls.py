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
    # Reports
    path("reports/", views.reports_index, name="reports_index"),
    path("reports/arrivals-departures/", views.report_arrivals_departures, name="report_arrivals_departures"),
    path("reports/courtesy-call-completion/", views.report_courtesy_call_completion, name="report_courtesy_call_completion"),
    path("reports/in-house-guests/", views.report_in_house_guests, name="report_in_house_guests"),
    path("reports/departure-outcomes/", views.report_departure_outcomes, name="report_departure_outcomes"),
    path("reports/agent-performance/", views.report_agent_performance, name="report_agent_performance"),
    path("reports/overdue-actions/", views.report_overdue_actions, name="report_overdue_actions"),
    path("reports/guest-feedback/", views.report_guest_feedback, name="report_guest_feedback"),
    path("reports/nationality-country-breakdown/", views.report_nationality_country_breakdown, name="report_nationality_country_breakdown"),
    path("reports/length-of-stay/", views.report_length_of_stay, name="report_length_of_stay"),
    path("reports/contact-completeness/", views.report_contact_completeness, name="report_contact_completeness"),
]


