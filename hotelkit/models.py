from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from datetime import timedelta


class RepairRequest(models.Model):
    """
    Model for repair requests with fields matching the Excel structure exactly.
    """
    position = models.IntegerField(
        help_text="Position in the original data"
    )
    id_field = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique ID for the repair request"
    )
    creator = models.CharField(
        max_length=200,
        help_text="Person who created the request"
    )
    recipients = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Recipients of the request"
    )
    location = models.CharField(
        max_length=200,
        help_text="Location where repair is needed"
    )
    location_path = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Full path to the location"
    )
    type = models.CharField(
        max_length=200,
        help_text="Type of repair request"
    )
    type_path = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Full path to the type"
    )
    assets = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Assets involved in the repair"
    )
    ticket = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Related ticket number"
    )
    creation_date = models.DateTimeField(
        help_text="When the request was created"
    )
    priority = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Priority level of the request"
    )
    state = models.CharField(
        max_length=100,
        help_text="Current state of the request"
    )
    latest_state_change_user = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="User who made the latest state change"
    )
    latest_state_change_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Time of the latest state change"
    )
    time_accepted = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the request was accepted"
    )
    time_in_progress = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When work started"
    )
    time_done = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the work was completed"
    )
    time_in_evaluation = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the request entered evaluation"
    )
    text = models.TextField(
        null=True,
        blank=True,
        help_text="Description of the request"
    )
    link = models.URLField(
        null=True,
        blank=True,
        help_text="Related link"
    )
    submitted_result = models.TextField(
        null=True,
        blank=True,
        help_text="Result submitted by technician"
    )
    comments = models.TextField(
        null=True,
        blank=True,
        help_text="Additional comments"
    )
    parking_reason = models.TextField(
        null=True,
        blank=True,
        help_text="Reason for parking the request"
    )
    parking_information = models.TextField(
        null=True,
        blank=True,
        help_text="Additional parking information"
    )
    
    # Calculated duration fields
    response_time = models.DurationField(
        null=True,
        blank=True,
        help_text="Time from creation to acceptance"
    )
    work_start_delay = models.DurationField(
        null=True,
        blank=True,
        help_text="Delay from acceptance to work start"
    )
    completion_time = models.DurationField(
        null=True,
        blank=True,
        help_text="Total time from creation to completion"
    )
    execution_time = models.DurationField(
        null=True,
        blank=True,
        help_text="Time spent on actual work"
    )
    evaluation_time = models.DurationField(
        null=True,
        blank=True,
        help_text="Time spent in evaluation"
    )
    latest_state_delay = models.DurationField(
        null=True,
        blank=True,
        help_text="Time from creation to latest state change"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-creation_date']
        verbose_name = "Repair Request"
        verbose_name_plural = "Repair Requests"

    def __str__(self):
        return f"{self.id_field} - {self.location} ({self.state})"

    def save(self, *args, **kwargs):
        """Override save to calculate duration fields automatically."""
        self.calculate_durations()
        super().save(*args, **kwargs)

    def calculate_durations(self):
        """Calculate all duration fields based on timestamps."""
        if self.creation_date:
            # Response time: Time accepted - Creation date
            if self.time_accepted:
                self.response_time = self.time_accepted - self.creation_date
            
            # Work start delay: Time in progress - Time accepted
            if self.time_accepted and self.time_in_progress:
                self.work_start_delay = self.time_in_progress - self.time_accepted
            
            # Completion time: Time done - Creation date
            if self.time_done:
                self.completion_time = self.time_done - self.creation_date
            
            # Execution time: Time done - Time in progress
            if self.time_in_progress and self.time_done:
                self.execution_time = self.time_done - self.time_in_progress
            
            # Evaluation time: Time "in evaluation" - Time done
            if self.time_done and self.time_in_evaluation:
                self.evaluation_time = self.time_in_evaluation - self.time_done
            
            # Latest state delay: Latest state change time - Creation date
            if self.latest_state_change_time:
                self.latest_state_delay = self.latest_state_change_time - self.creation_date

    @property
    def is_closed(self):
        """Check if the request is in a closed state."""
        closed_states = ['Closed', 'Done', 'Completed', 'Resolved']
        return self.state in closed_states

    @property
    def is_open(self):
        """Check if the request is still open."""
        return not self.is_closed

    @property
    def sla_4h_compliant(self):
        """Check if request was closed within 4 hours."""
        if not self.time_done or not self.creation_date:
            return False
        return self.completion_time <= timedelta(hours=4)

    @property
    def sla_24h_compliant(self):
        """Check if request was closed within 24 hours."""
        if not self.time_done or not self.creation_date:
            return False
        return self.completion_time <= timedelta(hours=24)

    @property
    def sla_48h_compliant(self):
        """Check if request was closed within 48 hours."""
        if not self.time_done or not self.creation_date:
            return False
        return self.completion_time <= timedelta(hours=48)