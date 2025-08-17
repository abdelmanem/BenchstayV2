from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

@login_required
@require_POST
def clear_cache(request):
    """
    View function to clear Django's cache
    """
    try:
        # Clear the entire cache
        cache.clear()
        return JsonResponse({'status': 'success', 'message': 'Cache cleared successfully'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)