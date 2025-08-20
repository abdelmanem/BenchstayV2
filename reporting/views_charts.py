from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Avg, Sum, F, ExpressionWrapper, DecimalField, Count, Q
from django.http import HttpResponse, JsonResponse
from datetime import timedelta, datetime
import json

from hotel_management.models import Hotel, Competitor, DailyData, CompetitorData, MarketSummary, PerformanceIndex
from accounts.models import UserProfile, SystemSettings

@login_required
def competitor_charts(request):
    """View for generating and viewing competitor charts"""
    hotel = Hotel.objects.first()
    competitors = Competitor.objects.filter(is_active=True)
    
    # If no hotel exists yet, redirect to hotel data page
    if not hotel:
        messages.info(request, 'Please set up your hotel information first')
        return redirect('hotel_management:hotel_data')
    
    # If no competitors exist, redirect to competitors page
    if not competitors.exists():
        messages.info(request, 'Please add competitors first')
        return redirect('hotel_management:competitors')
    
    # Default to last 30 days
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Invalid date format. Please use YYYY-MM-DD format.')
    
    # Calculate date ranges for different periods
    today = timezone.now().date()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    
    # Get data for different periods
    daily_data = prepare_chart_data(hotel, competitors, start_date, end_date)
    mtd_data = prepare_chart_data(hotel, competitors, month_start, today)
    ytd_data = prepare_chart_data(hotel, competitors, year_start, today)
    
    context = {
        'title': 'Competitor Charts - Benchstay',
        'hotel': hotel,
        'competitors': competitors,
        'start_date': start_date,
        'end_date': end_date,
        'daily_data': json.dumps(daily_data),
        'mtd_data': json.dumps(mtd_data),
        'ytd_data': json.dumps(ytd_data),
        'system_settings': SystemSettings.objects.first(),
    }
    
    return render(request, 'reporting/competitor_charts.html', context)

@login_required
def competitor_analytics_charts(request):
    """View for generating and viewing advanced competitor analytics charts"""
    hotel = Hotel.objects.first()
    competitors = Competitor.objects.filter(is_active=True)
    
    # If no hotel exists yet, redirect to hotel data page
    if not hotel:
        messages.info(request, 'Please set up your hotel information first')
        return redirect('hotel_management:hotel_data')
    
    # If no competitors exist, redirect to competitors page
    if not competitors.exists():
        messages.info(request, 'Please add competitors first')
        return redirect('hotel_management:competitors')
    
    # Default to last 30 days
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Invalid date format. Please use YYYY-MM-DD format.')
    
    # Calculate date ranges for different periods
    today = timezone.now().date()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    
    # Get data for different periods with more detailed analytics
    daily_data = prepare_advanced_chart_data(hotel, competitors, start_date, end_date)
    mtd_data = prepare_advanced_chart_data(hotel, competitors, month_start, today)
    ytd_data = prepare_advanced_chart_data(hotel, competitors, year_start, today)
    
    context = {
        'title': 'Advanced Competitor Analytics Charts - Benchstay',
        'hotel': hotel,
        'competitors': competitors,
        'start_date': start_date,
        'end_date': end_date,
        'daily_data': json.dumps(daily_data),
        'mtd_data': json.dumps(mtd_data),
        'ytd_data': json.dumps(ytd_data),
        'system_settings': SystemSettings.objects.first(),
    }
    
    return render(request, 'reporting/competitor_analytics_charts.html', context)

@login_required
def competitor_data_visualization(request):
    """View for generating and viewing competitor data visualizations"""
    hotel = Hotel.objects.first()
    competitors = Competitor.objects.filter(is_active=True)
    
    # If no hotel exists yet, redirect to hotel data page
    if not hotel:
        messages.info(request, 'Please set up your hotel information first')
        return redirect('hotel_management:hotel_data')
    
    # If no competitors exist, redirect to competitors page
    if not competitors.exists():
        messages.info(request, 'Please add competitors first')
        return redirect('hotel_management:competitors')
    
    # Default to last 30 days
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Invalid date format. Please use YYYY-MM-DD format.')
    
    # Calculate date ranges for different periods
    today = timezone.now().date()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    
    # Get data for different periods with visualization-specific formatting
    daily_data = prepare_visualization_data(hotel, competitors, start_date, end_date)
    mtd_data = prepare_visualization_data(hotel, competitors, month_start, today)
    ytd_data = prepare_visualization_data(hotel, competitors, year_start, today)
    
    context = {
        'title': 'Competitor Data Visualization - Benchstay',
        'hotel': hotel,
        'competitors': competitors,
        'start_date': start_date,
        'end_date': end_date,
        'daily_data': json.dumps(daily_data),
        'mtd_data': json.dumps(mtd_data),
        'ytd_data': json.dumps(ytd_data),
        'system_settings': SystemSettings.objects.first(),
    }
    
    return render(request, 'reporting/competitor_data_visualization.html', context)

def prepare_chart_data(hotel, competitors, start_date, end_date):
    """Prepare data for competitor charts"""
    data = {}
    
    # Get hotel data
    hotel_data = DailyData.objects.filter(
        hotel=hotel,
        date__gte=start_date,
        date__lte=end_date
    )
    
    # Calculate hotel metrics
    hotel_rooms_sold = hotel_data.aggregate(Sum('rooms_sold'))['rooms_sold__sum'] or 0
    hotel_occupancy = hotel_data.aggregate(Avg('occupancy_percentage'))['occupancy_percentage__avg'] or 0
    hotel_avg_rate = hotel_data.aggregate(Avg('average_rate'))['average_rate__avg'] or 0
    hotel_revpar = hotel_data.aggregate(Avg('revpar'))['revpar__avg'] or 0
    
    # Get hotel performance indices
    hotel_performance = PerformanceIndex.objects.filter(
        hotel=hotel,
        competitor=None,  # Only get hotel's own indices
        date__gte=start_date,
        date__lte=end_date
    )
    
    hotel_mpi = hotel_performance.aggregate(Avg('mpi'))['mpi__avg'] or 0
    hotel_ari = hotel_performance.aggregate(Avg('ari'))['ari__avg'] or 0
    hotel_rgi = hotel_performance.aggregate(Avg('rgi'))['rgi__avg'] or 0
    
    # Add hotel data to the result
    data[hotel.name] = {
        'occupancy_percentage': float(hotel_occupancy),
        'average_rate': float(hotel_avg_rate),
        'revpar': float(hotel_revpar),
        'mpi': float(hotel_mpi),
        'ari': float(hotel_ari),
        'rgi': float(hotel_rgi)
    }
    
    # Add competitor data
    for competitor in competitors:
        comp_data = CompetitorData.objects.filter(
            competitor=competitor,
            date__gte=start_date,
            date__lte=end_date
        )
        
        comp_occupancy = comp_data.aggregate(Avg('estimated_occupancy'))['estimated_occupancy__avg'] or 0
        comp_avg_rate = comp_data.aggregate(Avg('estimated_average_rate'))['estimated_average_rate__avg'] or 0
        comp_revpar = comp_data.aggregate(Avg('revpar'))['revpar__avg'] or 0
        
        # Get competitor performance indices
        comp_performance = PerformanceIndex.objects.filter(
            hotel=hotel,
            competitor=competitor,
            date__gte=start_date,
            date__lte=end_date
        )
        
        comp_mpi = comp_performance.aggregate(Avg('mpi'))['mpi__avg'] or 0
        comp_ari = comp_performance.aggregate(Avg('ari'))['ari__avg'] or 0
        comp_rgi = comp_performance.aggregate(Avg('rgi'))['rgi__avg'] or 0
        
        data[competitor.name] = {
            'occupancy_percentage': float(comp_occupancy),
            'average_rate': float(comp_avg_rate),
            'revpar': float(comp_revpar),
            'mpi': float(comp_mpi),
            'ari': float(comp_ari),
            'rgi': float(comp_rgi)
        }
    
    return data

def prepare_advanced_chart_data(hotel, competitors, start_date, end_date):
    """Prepare advanced data for competitor analytics charts"""
    # This function extends the basic chart data with more detailed metrics
    data = prepare_chart_data(hotel, competitors, start_date, end_date)
    
    # Get market summary data
    market_summaries = MarketSummary.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    )
    
    # Calculate market averages
    market_occupancy = market_summaries.aggregate(Avg('market_occupancy'))['market_occupancy__avg'] or 0
    market_adr = market_summaries.aggregate(Avg('market_adr'))['market_adr__avg'] or 0
    market_revpar = market_summaries.aggregate(Avg('market_revpar'))['market_revpar__avg'] or 0
    
    # Add market data
    data['Market Average'] = {
        'occupancy_percentage': float(market_occupancy),
        'average_rate': float(market_adr),
        'revpar': float(market_revpar),
        'mpi': 100.0,  # Market is the baseline
        'ari': 100.0,
        'rgi': 100.0
    }
    
    return data

def prepare_visualization_data(hotel, competitors, start_date, end_date):
    """Prepare data specifically formatted for visualizations"""
    # Start with the advanced data
    data = prepare_advanced_chart_data(hotel, competitors, start_date, end_date)
    
    # Add any visualization-specific data transformations here
    # For example, calculating trends, growth rates, etc.
    
    # Calculate day-by-day data for trend visualization
    date_range = (end_date - start_date).days + 1
    daily_trends = {}
    
    for i in range(date_range):
        current_date = start_date + timedelta(days=i)
        daily_trends[current_date.strftime('%Y-%m-%d')] = {}
        
        # Get hotel data for this day
        hotel_day_data = DailyData.objects.filter(hotel=hotel, date=current_date).first()
        if hotel_day_data:
            daily_trends[current_date.strftime('%Y-%m-%d')][hotel.name] = {
                'occupancy_percentage': float(hotel_day_data.occupancy_percentage),
                'average_rate': float(hotel_day_data.average_rate),
                'revpar': float(hotel_day_data.revpar)
            }
        
        # Get competitor data for this day
        for competitor in competitors:
            comp_day_data = CompetitorData.objects.filter(competitor=competitor, date=current_date).first()
            if comp_day_data:
                daily_trends[current_date.strftime('%Y-%m-%d')][competitor.name] = {
                    'occupancy_percentage': float(comp_day_data.estimated_occupancy),
                    'average_rate': float(comp_day_data.estimated_average_rate),
                    'revpar': float(comp_day_data.revpar)
                }
    
    # Add the daily trends to the data
    data['daily_trends'] = daily_trends
    
    return data