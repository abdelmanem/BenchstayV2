from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    position = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    is_admin = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"


class SystemSettings(models.Model):
    # Currency settings
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar ($)'),
        ('EUR', 'Euro (€)'),
        ('GBP', 'British Pound (£)'),
        ('JPY', 'Japanese Yen (¥)'),
        ('AUD', 'Australian Dollar (A$)'),
        ('CAD', 'Canadian Dollar (C$)'),
        ('CHF', 'Swiss Franc (CHF)'),
        ('CNY', 'Chinese Yuan (¥)'),
        ('EGP', 'Egyptian Pound (E£)'),
        ('SAR', 'Saudi Riyal (﷼)'),
        ('AED', 'UAE Dirham (د.إ)'),
    ]
    
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    currency_symbol = models.CharField(max_length=5, blank=True, help_text='Custom currency symbol if needed')
    
    # Date format settings
    DATE_FORMAT_CHOICES = [
        ('MM/DD/YYYY', 'MM/DD/YYYY'),
        ('DD/MM/YYYY', 'DD/MM/YYYY'),
        ('YYYY-MM-DD', 'YYYY-MM-DD'),
    ]
    date_format = models.CharField(max_length=10, choices=DATE_FORMAT_CHOICES, default='MM/DD/YYYY')
    
    # System settings
    system_name = models.CharField(max_length=100, default='Benchstay')
    system_version = models.CharField(max_length=20, default='2.0.0')
    company_name = models.CharField(max_length=100, blank=True, null=True)
    company_logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    support_email = models.EmailField(blank=True, null=True)
    
    # Email settings
    enable_email_notifications = models.BooleanField(default=True)
    
    # Number formatting settings
    decimal_places_percentage = models.IntegerField(default=1, help_text='Decimal places for percentages (e.g., occupancy, indices)')
    decimal_places_currency = models.IntegerField(default=2, help_text='Decimal places for currency values (e.g., ADR, RevPAR)')

    # Performance settings
    items_per_page = models.IntegerField(default=25, help_text='Number of items to display per page in tables')
    
    # Singleton pattern - only one instance of settings should exist
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'System Settings'
        verbose_name_plural = 'System Settings'
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if not self.pk and SystemSettings.objects.exists():
            # Update existing settings instead of creating new ones
            return SystemSettings.objects.first().save(*args, **kwargs)
        return super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Get or create system settings"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
    
    def get_currency_symbol(self):
        """Get the currency symbol for the selected currency"""
        currency_symbols = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'JPY': '¥',
            'AUD': 'A$',
            'CAD': 'C$',
            'CHF': 'CHF',
            'CNY': '¥',
            'EGP': 'E£',
            'SAR': '﷼',
            'AED': 'د.إ',
        }
        return currency_symbols.get(self.currency, '$')
    
    @property
    def effective_currency_symbol(self):
        """Get the effective currency symbol (custom if set, otherwise default)"""
        if self.currency_symbol:
            return self.currency_symbol
        return self.get_currency_symbol()

    def clamp_decimal_places(self, value: int) -> int:
        """Ensure decimal places are within a sane range 0-3."""
        try:
            v = int(value)
        except (TypeError, ValueError):
            return 0
        return max(0, min(3, v))
    
    def __str__(self):
        return f"System Settings (Last updated: {self.updated_at})"
