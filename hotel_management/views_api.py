from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta, date
from calendar import monthrange
from .models import Hotel, Competitor, DailyData, CompetitorData, PerformanceIndex

@login_required
def revpar_matrix_api(request):
    """
    API endpoint for RevPAR Positioning Matrix data
    Accepts start_date and end_date parameters to filter data
    """
    # Get the user's hotel
    hotel = Hotel.objects.first()
    
    if not hotel:
        return JsonResponse({'error': 'Hotel not found'}, status=404)
    
    # Get date range from request
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    # Default to current month if no dates provided
    today = timezone.now().date()
    
    # Default: first day to last day of current month
    current_month = today.month
    current_year = today.year
    _, last_day = monthrange(current_year, current_month)
    start_date = date(current_year, current_month, 1)
    end_date = date(current_year, current_month, last_day)
    
    # Process custom date range if provided
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Please use YYYY-MM-DD format.'}, status=400)
    
    # Get performance indices for the hotel in the date range
    latest_indices = PerformanceIndex.objects.filter(
        hotel=hotel,
        date__gte=start_date,
        date__lte=end_date,
        competitor__isnull=True  # Only get hotel's own indices
    ).order_by('-date').first()
    
    # Get data for RevPAR positioning matrix
    hotel_data = {
        'occupancy_index': latest_indices.mpi if latest_indices else 0,
        'adr_index': latest_indices.ari if latest_indices else 0
    }
    
    # Get competitor data for the date range
    competitor_data = []
    for comp in Competitor.objects.filter(is_active=True):
        latest_comp_data = CompetitorData.objects.filter(
            competitor=comp,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('-date').first()
        
        if latest_comp_data:
            competitor_data.append({
                'x': latest_comp_data.occupancy_index,
                'y': latest_comp_data.adr_index,
                'name': comp.name
            })
    
    # Return the data as JSON
    from django.http import HttpResponse
    from .json_utils import decimal_safe_dumps
    import json
    
    # Use the custom JSON encoder to handle Decimal objects
    response_data = {
        'hotel_data': hotel_data,
        'competitor_data': competitor_data,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat()
    }
    
    return HttpResponse(
        decimal_safe_dumps(response_data),
        content_type='application/json'
    )