from django.db import models
from django.contrib.auth.models import User


class ArrivalRecord(models.Model):
    """
    Stores arrivals imported from the Excel report.

    Adjust field names/types to match your real Excel structure if needed.
    """

    # Raw columns from Excel
    property_name = models.CharField(max_length=255, blank=True)
    confirmation_number = models.CharField(max_length=100, blank=True)
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    room = models.CharField(max_length=20, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    arrival_date = models.DateField(null=True, blank=True)
    departure_date = models.DateField(null=True, blank=True)
    travel_agent_name = models.CharField(max_length=255, blank=True)

    # Derived / display fields
    guest_name = models.CharField(max_length=255, blank=True)
    eta = models.CharField(max_length=20, blank=True)  # keep as text to avoid parsing issues
    nights = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=50, blank=True)

    # Courtesy call tracking
    in_house_since = models.DateTimeField(null=True, blank=True)
    in_house_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="arrival_records_in_house")
    first_courtesy_due_at = models.DateTimeField(null=True, blank=True)
    first_courtesy_done_at = models.DateTimeField(null=True, blank=True)
    first_courtesy_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="arrival_records_first_courtesy")
    second_courtesy_due_at = models.DateTimeField(null=True, blank=True)
    second_courtesy_done_at = models.DateTimeField(null=True, blank=True)
    second_courtesy_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="arrival_records_second_courtesy")
    first_courtesy_outcome = models.CharField(max_length=100, blank=True)
    first_courtesy_notes = models.TextField(blank=True)
    second_courtesy_outcome = models.CharField(max_length=100, blank=True)
    second_courtesy_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="arrival_records_created")
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="arrival_records_updated")

    class Meta:
        ordering = ["arrival_date", "room"]

    def __str__(self):
        return f"{self.arrival_date} - {self.room} - {self.guest_name}"
