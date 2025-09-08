from django.db import models
from django import forms


class GuestRequest(models.Model):
    """Guest request imported from external Excel exports."""

    request_id = models.CharField(max_length=100, unique=True)
    creator = models.CharField(max_length=255)
    recipients = models.CharField(max_length=255)
    location = models.CharField(max_length=255, null=True, blank=True)
    location_path = models.CharField(max_length=512, null=True, blank=True)
    type = models.CharField(max_length=255, null=True, blank=True)
    type_path = models.CharField(max_length=512, null=True, blank=True)
    assets = models.TextField(null=True, blank=True)
    ticket = models.CharField(max_length=255, null=True, blank=True)
    creation_date = models.DateTimeField()
    priority = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    latest_state_change_user = models.CharField(max_length=255, null=True, blank=True)
    latest_state_change_time = models.DateTimeField(null=True, blank=True)
    time_accepted = models.DateTimeField(null=True, blank=True)
    time_in_progress = models.DateTimeField(null=True, blank=True)
    time_done = models.DateTimeField(null=True, blank=True)
    time_in_evaluation = models.DateTimeField(null=True, blank=True)

    text = models.TextField(null=True, blank=True)
    link = models.URLField(null=True, blank=True)
    submitted_result = models.TextField(null=True, blank=True)
    comments = models.TextField(null=True, blank=True)

    response_time = models.DurationField(null=True, blank=True)
    completion_time = models.DurationField(null=True, blank=True)
    total_duration = models.DurationField(null=True, blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'hotelkit'
        ordering = ['-creation_date']

    def save(self, *args, **kwargs):
        # Compute durations based on available datetimes
        if self.creation_date and self.time_accepted:
            self.response_time = self.time_accepted - self.creation_date
        else:
            self.response_time = None

        if self.creation_date and self.time_done:
            self.completion_time = self.time_done - self.creation_date
        else:
            self.completion_time = None

        if self.time_done and self.time_accepted:
            self.total_duration = self.time_done - self.time_accepted
        else:
            self.total_duration = None

        super().save(*args, **kwargs)



class GuestRequestForm(forms.ModelForm):
    class Meta:
        model = GuestRequest
        fields = [
            'state',
            'priority',
            'recipients',
            'location',
            'type',
            'time_accepted',
            'time_done',
        ]
        widgets = {
            'time_accepted': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'time_done': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

