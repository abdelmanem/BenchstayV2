from accounts.models import SystemSettings

def system_settings(request):
    """
    Context processor that adds system_settings to the context of all templates.
    This makes currency, date format, and other system settings available globally.
    """
    return {
        'system_settings': SystemSettings.get_settings()
    }