from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
import json

# Create your models here.
class Hotel(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    total_rooms = models.IntegerField()
    logo = models.ImageField(upload_to='hotel_logos/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class Competitor(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive')
    ]
    name = models.CharField(max_length=200)
    address = models.TextField()
    total_rooms = models.IntegerField()
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class DailyData(models.Model):
    date = models.DateField()
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='daily_data')
    rooms_sold = models.IntegerField()
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    average_rate = models.DecimalField(max_digits=8, decimal_places=2)
    occupancy_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    revpar = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='RevPAR')
    total_rooms = models.IntegerField(default=0)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['date', 'hotel']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.hotel.name} - {self.date}"
    
    def save(self, *args, **kwargs):
        try:
            # Ensure total_revenue is a Decimal
            if isinstance(self.total_revenue, str):
                self.total_revenue = Decimal(self.total_revenue)
                
            # Convert to proper types before comparisons
            rooms_sold = int(self.rooms_sold)
            # Use stored total_rooms value, or get from hotel if not set yet
            if self.total_rooms > 0:
                total_rooms = int(self.total_rooms)
            else:
                total_rooms = int(self.hotel.total_rooms) if self.hotel and hasattr(self.hotel, 'total_rooms') else 0
                # Store the total_rooms value for future use
                self.total_rooms = total_rooms
            
            # Calculate average rate if rooms_sold > 0
            if rooms_sold > 0:
                # Make sure both operands are Decimal
                self.average_rate = Decimal(str(self.total_revenue)) / Decimal(rooms_sold)
            else:
                self.average_rate = Decimal('0.00')
            
            # Calculate occupancy percentage
            if total_rooms > 0:
                self.occupancy_percentage = (Decimal(rooms_sold) / Decimal(total_rooms)) * Decimal('100')
            else:
                self.occupancy_percentage = Decimal('0.00')
            
            # Calculate RevPAR
            if total_rooms > 0:
                # Make sure both operands are Decimal
                self.revpar = Decimal(str(self.total_revenue)) / Decimal(total_rooms)
            else:
                self.revpar = Decimal('0.00')
                
        except (ValueError, TypeError) as e:
            # Print more debugging information
            print(f"Error in DailyData.save(): {e}")
            print(f"Type of total_revenue: {type(self.total_revenue)}")
            print(f"Value of total_revenue: {self.total_revenue}")
            print(f"Type of rooms_sold: {type(self.rooms_sold)}")
            print(f"Value of rooms_sold: {self.rooms_sold}")
            raise
        
        super().save(*args, **kwargs)
        
        # After saving, update market summary and performance indices
        from .utils import update_market_summary
        # Update market summary and performance indices
        update_market_summary(self.date, skip_performance_update=False)

class CompetitorData(models.Model):
    date = models.DateField()
    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name='daily_data')
    rooms_sold = models.IntegerField()
    estimated_occupancy = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    estimated_average_rate = models.DecimalField(max_digits=8, decimal_places=2)
    # RevPAR is still calculated in the model for convenience
    revpar = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='RevPAR', null=True, blank=True)
    total_rooms = models.IntegerField(default=0)
    # Performance indices
    occupancy_index = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    adr_index = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    revenue_index = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['date', 'competitor']
    
    def __str__(self):
        return f"{self.competitor.name} - {self.date}"
    
    def save(self, *args, **kwargs):
        # Check if we're updating specific fields only
        update_fields = kwargs.get('update_fields')
        if update_fields and all(field in ['occupancy_index', 'adr_index', 'revenue_index'] for field in update_fields):
            # If we're only updating indices, skip the recalculation and market summary update
            super().save(*args, **kwargs)
            return
            
        try:
            # Convert to proper types before calculations
            rooms_sold = int(self.rooms_sold)
            # Use stored total_rooms value, or get from competitor if not set yet
            if self.total_rooms > 0:
                total_rooms = int(self.total_rooms)
            else:
                total_rooms = int(self.competitor.total_rooms) if self.competitor and hasattr(self.competitor, 'total_rooms') else 0
                # Store the total_rooms value for future use
                self.total_rooms = total_rooms
            
            # Calculate estimated occupancy if rooms_sold is provided and total_rooms > 0
            if rooms_sold is not None and total_rooms > 0:
                self.estimated_occupancy = (Decimal(str(rooms_sold)) / Decimal(str(total_rooms))) * Decimal('100')
            else:
                self.estimated_occupancy = Decimal('0.00')
            
            # Calculate RevPAR
            room_revenue = Decimal(str(rooms_sold)) * Decimal(str(self.estimated_average_rate))
            if total_rooms > 0:
                self.revpar = room_revenue / Decimal(str(total_rooms))
            else:
                self.revpar = Decimal('0.00')
                
        except (ValueError, TypeError) as e:
            # Print debugging information
            print(f"Error in CompetitorData.save(): {e}")
            print(f"Type of rooms_sold: {type(self.rooms_sold)}")
            print(f"Value of rooms_sold: {self.rooms_sold}")
            print(f"Type of total_rooms: {type(self.competitor.total_rooms)}")
            print(f"Value of total_rooms: {self.competitor.total_rooms}")
            raise
            
        super().save(*args, **kwargs)
        
        # After saving, update market summary and performance indices
        from .utils import update_market_summary
        # Allow performance update for CompetitorData since it's the final step
        update_market_summary(self.date, skip_performance_update=False)

class MarketSummary(models.Model):
    date = models.DateField(unique=True)
    total_rooms_available = models.IntegerField()
    total_rooms_sold = models.IntegerField()
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    market_occupancy = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    market_adr = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='Market ADR')
    market_revpar = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='Market RevPAR')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'Market Summaries'
    
    def __str__(self):
        return f"Market Summary - {self.date}"
    
    def save(self, *args, **kwargs):
        # Calculate market metrics
        if self.total_rooms_available > 0:
            self.market_occupancy = (Decimal(self.total_rooms_sold) / Decimal(self.total_rooms_available)) * Decimal('100')
        else:
            self.market_occupancy = Decimal('0.00')
            
        if self.total_rooms_sold > 0:
            self.market_adr = self.total_revenue / Decimal(self.total_rooms_sold)
        else:
            self.market_adr = Decimal('0.00')
            
        if self.total_rooms_available > 0:
            self.market_revpar = self.total_revenue / Decimal(self.total_rooms_available)
        else:
            self.market_revpar = Decimal('0.00')
            
        super().save(*args, **kwargs)

class PerformanceIndex(models.Model):
    date = models.DateField()
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='performance_indices')
    competitor = models.ForeignKey(Competitor, on_delete=models.CASCADE, related_name='performance_indices', null=True, blank=True)
    market_summary = models.ForeignKey(MarketSummary, on_delete=models.CASCADE, related_name='performance_indices')
    
    fair_market_share = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    actual_market_share = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    mpi = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='MPI', null=True, blank=True)
    ari = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='ARI', null=True, blank=True)
    rgi = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='RGI', null=True, blank=True)
    mpi_rank = models.IntegerField(null=True, blank=True)
    ari_rank = models.IntegerField(null=True, blank=True)
    rgi_rank = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['date', 'hotel', 'competitor']
        ordering = ['-date']
    
    def __str__(self):
        if self.competitor:
            return f"{self.hotel.name} vs {self.competitor.name} - {self.date}"
        return f"{self.hotel.name} - {self.date}"

class AuditLog(models.Model):
    ENTITY_TYPES = [
        ('hotel', 'Hotel'),
        ('competitor', 'Competitor')
    ]
    
    ACTION_TYPES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete')
    ]
    
    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPES)
    entity_id = models.IntegerField()
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    changes = models.JSONField()
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    performed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-performed_at']  # Changed from created_at to performed_at
    
    def __str__(self):
        return f"{self.entity_type} {self.entity_id} - {self.action} by {self.performed_by} at {self.performed_at}"