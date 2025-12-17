from django.db import models


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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["arrival_date", "room"]

    def __str__(self):
        return f"{self.arrival_date} - {self.room} - {self.guest_name}"
