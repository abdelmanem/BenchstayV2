from django.db import models
from django.contrib.auth.models import User
from hotel_management.models import Hotel, Competitor

# Create your models here.
class ReportConfiguration(models.Model):
    REPORT_TYPES = (
        ('revenue', 'Revenue Report'),
        ('occupancy', 'Occupancy Report'),
        ('competitor', 'Competitor Analysis'),
        ('custom', 'Custom Report'),
    )
    
    PERIOD_TYPES = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom Range'),
    )
    
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    period_type = models.CharField(max_length=20, choices=PERIOD_TYPES)
    include_competitors = models.BooleanField(default=False)
    competitors = models.ManyToManyField(Competitor, blank=True)
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='report_configs')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.get_report_type_display()}"

class SavedReport(models.Model):
    configuration = models.ForeignKey(ReportConfiguration, on_delete=models.CASCADE, related_name='saved_reports')
    title = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    report_data = models.JSONField()  # Store the report data as JSON
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.start_date} to {self.end_date})"
