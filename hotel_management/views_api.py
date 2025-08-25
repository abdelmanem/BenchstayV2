from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta, date
from calendar import monthrange
from django.db.models import Avg, Sum
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
        'x': float(latest_indices.mpi) if latest_indices and latest_indices.mpi else 100,
        'y': float(latest_indices.ari) if latest_indices and latest_indices.ari else 100
    }
    
    # Get competitor data for the matrix
    competitor_data = []
    for comp in Competitor.objects.filter(is_active=True):
        latest_comp_data = CompetitorData.objects.filter(
            competitor=comp,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('-date').first()
        
        if latest_comp_data:
            competitor_data.append({
                'x': float(latest_comp_data.occupancy_index) if latest_comp_data.occupancy_index else 100,
                'y': float(latest_comp_data.adr_index) if latest_comp_data.adr_index else 100,
                'name': comp.name
            })
    
    return JsonResponse({
        'hotel_data': hotel_data,
        'competitor_data': competitor_data,
        'date_range': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
    })

@login_required
def chart_data_api(request):
    """
    API endpoint for chart data (occupancy, ADR, RevPAR)
    Accepts start_date, end_date, and metric_type parameters
    """
    hotel = Hotel.objects.first()
    
    if not hotel:
        return JsonResponse({'error': 'Hotel not found'}, status=404)
    
    # Get parameters from request
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    metric_type = request.GET.get('metric_type', 'all')  # occupancy, adr, revpar, or all
    
    # Default to current month if no dates provided
    today = timezone.now().date()
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
    
    # Get hotel data for the selected period
    hotel_data = DailyData.objects.filter(
        hotel=hotel,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date')
    
    # Calculate prior year date range (same period last year)
    days_diff = (end_date - start_date).days
    prior_year_start_date = date(start_date.year - 1, start_date.month, start_date.day)
    prior_year_end_date = prior_year_start_date + timedelta(days=days_diff)
    
    # Get prior year data
    prior_year_data = DailyData.objects.filter(
        hotel=hotel,
        date__gte=prior_year_start_date,
        date__lte=prior_year_end_date
    ).order_by('date')
    
    # Prepare response data
    response_data = {
        'labels': [],
        'current': {},
        'previous': {},
        'date_range': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'prior_start_date': prior_year_start_date.isoformat(),
            'prior_end_date': prior_year_end_date.isoformat()
        }
    }
    
    # Generate date labels (monthly or daily based on date range)
    if days_diff > 90:  # More than 3 months, use monthly labels
        current_date = start_date.replace(day=1)
        while current_date <= end_date:
            response_data['labels'].append(current_date.strftime('%b %Y'))
            current_date = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)
    else:  # Use daily labels
        current_date = start_date
        while current_date <= end_date:
            response_data['labels'].append(current_date.strftime('%b %d'))
            current_date += timedelta(days=1)
    
    # Get data for each metric type
    if metric_type in ['occupancy', 'all']:
        response_data['current']['occupancy'] = []
        response_data['previous']['occupancy'] = []
        
        # Current year data
        for label in response_data['labels']:
            if days_diff > 90:  # Monthly data
                month_year = datetime.strptime(label, '%b %Y')
                month_data = hotel_data.filter(date__year=month_year.year, date__month=month_year.month)
                avg_occ = month_data.aggregate(Avg('occupancy_percentage'))['occupancy_percentage__avg'] or 0
                response_data['current']['occupancy'].append(float(avg_occ))
            else:  # Daily data
                # For daily data, we'll use the first available data point for each day
                # This is a simplified approach - in production you might want more sophisticated date matching
                if hotel_data.exists():
                    first_data = hotel_data.first()
                    response_data['current']['occupancy'].append(float(first_data.occupancy_percentage))
                else:
                    response_data['current']['occupancy'].append(0)
        
        # Prior year data
        for label in response_data['labels']:
            if days_diff > 90:  # Monthly data
                month_year = datetime.strptime(label, '%b %Y')
                month_data = prior_year_data.filter(date__year=month_year.year, date__month=month_year.month)
                avg_occ = month_data.aggregate(Avg('occupancy_percentage'))['occupancy_percentage__avg'] or 0
                response_data['previous']['occupancy'].append(float(avg_occ))
            else:  # Daily data
                # For daily data, we'll use the first available data point for each day
                if prior_year_data.exists():
                    first_data = prior_year_data.first()
                    response_data['previous']['occupancy'].append(float(first_data.occupancy_percentage))
                else:
                    response_data['previous']['occupancy'].append(0)
    
    if metric_type in ['adr', 'all']:
        response_data['current']['adr'] = []
        response_data['previous']['adr'] = []
        
        # Current year data
        for label in response_data['labels']:
            if days_diff > 90:  # Monthly data
                month_year = datetime.strptime(label, '%b %Y')
                month_data = hotel_data.filter(date__year=month_year.year, date__month=month_year.month)
                avg_adr = month_data.aggregate(Avg('average_rate'))['average_rate__avg'] or 0
                response_data['current']['adr'].append(float(avg_adr))
            else:  # Daily data
                # For daily data, we'll use the first available data point for each day
                if hotel_data.exists():
                    first_data = hotel_data.first()
                    response_data['current']['adr'].append(float(first_data.average_rate))
                else:
                    response_data['current']['adr'].append(0)
        
        # Prior year data
        for label in response_data['labels']:
            if days_diff > 90:  # Monthly data
                month_year = datetime.strptime(label, '%b %Y')
                month_data = prior_year_data.filter(date__year=month_year.year, date__month=month_year.month)
                avg_adr = month_data.aggregate(Avg('average_rate'))['average_rate__avg'] or 0
                response_data['previous']['adr'].append(float(avg_adr))
            else:  # Daily data
                # For daily data, we'll use the first available data point for each day
                if prior_year_data.exists():
                    first_data = prior_year_data.first()
                    response_data['previous']['adr'].append(float(first_data.average_rate))
                else:
                    response_data['previous']['adr'].append(0)
    
    if metric_type in ['revpar', 'all']:
        response_data['current']['revpar'] = []
        response_data['previous']['revpar'] = []
        
        # Current year data
        for label in response_data['labels']:
            if days_diff > 90:  # Monthly data
                month_year = datetime.strptime(label, '%b %Y')
                month_data = hotel_data.filter(date__year=month_year.year, date__month=month_year.month)
                avg_revpar = month_data.aggregate(Avg('revpar'))['revpar__avg'] or 0
                response_data['current']['revpar'].append(float(avg_revpar))
            else:  # Daily data
                # For daily data, we'll use the first available data point for each day
                if hotel_data.exists():
                    first_data = hotel_data.first()
                    response_data['current']['revpar'].append(float(first_data.revpar))
                else:
                    response_data['current']['revpar'].append(0)
        
        # Prior year data
        for label in response_data['labels']:
            if days_diff > 90:  # Monthly data
                month_year = datetime.strptime(label, '%b %Y')
                month_data = prior_year_data.filter(date__year=month_year.year, date__month=month_year.month)
                avg_revpar = month_data.aggregate(Avg('revpar'))['revpar__avg'] or 0
                response_data['previous']['revpar'].append(float(avg_revpar))
            else:  # Daily data
                # For daily data, we'll use the first available data point for each day
                if prior_year_data.exists():
                    first_data = prior_year_data.first()
                    response_data['previous']['revpar'].append(float(first_data.revpar))
                else:
                    response_data['previous']['revpar'].append(0)
    
    return JsonResponse(response_data)

@login_required
def performance_indices_api(request):
    """
    API endpoint for performance indices chart data (MPI, ARI, RGI)
    Accepts start_date and end_date parameters
    """
    hotel = Hotel.objects.first()
    
    if not hotel:
        return JsonResponse({'error': 'Hotel not found'}, status=404)
    
    # Get date range from request
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    # Default to current month if no dates provided
    today = timezone.now().date()
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
    performance_indices = PerformanceIndex.objects.filter(
        hotel=hotel,
        date__gte=start_date,
        date__lte=end_date,
        competitor__isnull=True  # Only get hotel's own indices
    ).order_by('date')
    
    # Calculate prior year date range (same period last year)
    days_diff = (end_date - start_date).days
    prior_year_start_date = date(start_date.year - 1, start_date.month, start_date.day)
    prior_year_end_date = prior_year_start_date + timedelta(days=days_diff)
    
    # Get prior year performance indices
    prior_year_indices = PerformanceIndex.objects.filter(
        hotel=hotel,
        date__gte=prior_year_start_date,
        date__lte=prior_year_end_date,
        competitor__isnull=True
    ).order_by('date')
    
    # Generate date labels
    response_data = {
        'labels': [],
        'current': {},
        'market': {},
        'date_range': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'prior_start_date': prior_year_start_date.isoformat(),
            'prior_end_date': prior_year_end_date.isoformat()
        }
    }
    
    # Generate date labels (monthly or daily based on date range)
    if days_diff > 90:  # More than 3 months, use monthly labels
        current_date = start_date.replace(day=1)
        while current_date <= end_date:
            response_data['labels'].append(current_date.strftime('%b %Y'))
            current_date = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)
    else:  # Use daily labels
        current_date = start_date
        while current_date <= end_date:
            response_data['labels'].append(current_date.strftime('%b %d'))
            current_date += timedelta(days=1)
    
    # Get MPI data
    response_data['current']['mpi'] = []
    response_data['market']['mpi'] = []
    
    for label in response_data['labels']:
        if days_diff > 90:  # Monthly data
            month_year = datetime.strptime(label, '%b %Y')
            month_data = performance_indices.filter(date__year=month_year.year, date__month=month_year.month)
            avg_mpi = month_data.aggregate(Avg('mpi'))['mpi__avg'] or 100
            response_data['current']['mpi'].append(float(avg_mpi))
        else:  # Daily data
            # For daily data, we'll use the first available data point for each day
            if performance_indices.exists():
                first_data = performance_indices.first()
                response_data['current']['mpi'].append(float(first_data.mpi or 100))
            else:
                response_data['current']['mpi'].append(100)
        
        # Market average is always 100 (baseline)
        response_data['market']['mpi'].append(100)
    
    # Get ARI data
    response_data['current']['ari'] = []
    response_data['market']['ari'] = []
    
    for label in response_data['labels']:
        if days_diff > 90:  # Monthly data
            month_year = datetime.strptime(label, '%b %Y')
            month_data = performance_indices.filter(date__year=month_year.year, date__month=month_year.month)
            avg_ari = month_data.aggregate(Avg('ari'))['ari__avg'] or 100
            response_data['current']['ari'].append(float(avg_ari))
        else:  # Daily data
            # For daily data, we'll use the first available data point for each day
            if performance_indices.exists():
                first_data = performance_indices.first()
                response_data['current']['ari'].append(float(first_data.ari or 100))
            else:
                response_data['current']['ari'].append(100)
        
        # Market average is always 100 (baseline)
        response_data['market']['ari'].append(100)
    
    # Get RGI data
    response_data['current']['rgi'] = []
    response_data['market']['rgi'] = []
    
    for label in response_data['labels']:
        if days_diff > 90:  # Monthly data
            month_year = datetime.strptime(label, '%b %Y')
            month_data = performance_indices.filter(date__year=month_year.year, date__month=month_year.month)
            avg_rgi = month_data.aggregate(Avg('rgi'))['rgi__avg'] or 100
            response_data['current']['rgi'].append(float(avg_rgi))
        else:  # Daily data
            # For daily data, we'll use the first available data point for each day
            if performance_indices.exists():
                first_data = performance_indices.first()
                response_data['current']['rgi'].append(float(first_data.rgi or 100))
            else:
                response_data['current']['rgi'].append(100)
        
        # Market average is always 100 (baseline)
        response_data['market']['rgi'].append(100)
    
    return JsonResponse(response_data)