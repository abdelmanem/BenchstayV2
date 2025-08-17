from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
from django.db.models import Sum, Avg
import json

from hotel_management.models import Hotel, Competitor, DailyData, CompetitorData, MarketSummary, PerformanceIndex

@login_required
@require_POST
def refresh_competitor_analytics(request):
    """AJAX endpoint to refresh competitor analytics data"""
    # Get the current hotel and competitors
    hotel = Hotel.objects.first()
    competitors = Competitor.objects.all()
    
    # Get date range from request
    start_date_str = request.POST.get('start_date')
    end_date_str = request.POST.get('end_date')
    
    # Default to today if no dates provided
    today = timezone.now().date()
    start_date = today
    end_date = today
    
    # Process custom date range if provided
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Please use YYYY-MM-DD format.'}, status=400)
    
    # Calculate date ranges for different periods
    today_date = today
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    
    # Get hotel data for different periods
    daily_hotel_data = DailyData.objects.filter(hotel=hotel, date__gte=start_date, date__lte=end_date)
    mtd_hotel_data = DailyData.objects.filter(hotel=hotel, date__gte=month_start, date__lte=today_date)
    ytd_hotel_data = DailyData.objects.filter(hotel=hotel, date__gte=year_start, date__lte=today_date)
    
    # Get competitor data for different periods
    daily_competitor_data = CompetitorData.objects.filter(competitor__in=competitors, date__gte=start_date, date__lte=end_date)
    mtd_competitor_data = CompetitorData.objects.filter(competitor__in=competitors, date__gte=month_start, date__lte=today_date)
    ytd_competitor_data = CompetitorData.objects.filter(competitor__in=competitors, date__gte=year_start, date__lte=today_date)
    
    # Initialize data structures for analytics
    daily_data = {}
    mtd_data = {}
    ytd_data = {}
    
    # Calculate daily metrics for hotel
    hotel_daily_rooms_available = hotel.total_rooms
    hotel_daily_rooms_sold = daily_hotel_data.aggregate(Sum('rooms_sold'))['rooms_sold__sum'] or 0
    hotel_daily_room_revenue = daily_hotel_data.aggregate(Sum('total_revenue'))['total_revenue__sum'] or 0
    hotel_daily_occupancy = daily_hotel_data.aggregate(Avg('occupancy_percentage'))['occupancy_percentage__avg'] or 0
    hotel_daily_avg_rate = daily_hotel_data.aggregate(Avg('average_rate'))['average_rate__avg'] or 0
    hotel_daily_revpar = daily_hotel_data.aggregate(Avg('revpar'))['revpar__avg'] or 0
    
    # Get performance indices for the date range
    daily_performance_indices = PerformanceIndex.objects.filter(
        hotel=hotel,
        competitor=None,  # Only get hotel's own indices
        date__gte=start_date,
        date__lte=end_date
    )
    
    # Calculate MTD metrics for hotel
    days_in_month = (today_date - month_start).days + 1
    hotel_mtd_rooms_available = hotel.total_rooms
    hotel_mtd_rooms_sold = mtd_hotel_data.aggregate(Sum('rooms_sold'))['rooms_sold__sum'] or 0
    hotel_mtd_room_revenue = mtd_hotel_data.aggregate(Sum('total_revenue'))['total_revenue__sum'] or 0
    hotel_mtd_occupancy = mtd_hotel_data.aggregate(Avg('occupancy_percentage'))['occupancy_percentage__avg'] or 0
    hotel_mtd_avg_rate = mtd_hotel_data.aggregate(Avg('average_rate'))['average_rate__avg'] or 0
    hotel_mtd_revpar = mtd_hotel_data.aggregate(Avg('revpar'))['revpar__avg'] or 0
    
    # Get MTD performance indices
    mtd_performance_indices = PerformanceIndex.objects.filter(
        hotel=hotel,
        competitor=None,  # Only get hotel's own indices
        date__gte=month_start,
        date__lte=today_date
    )
    
    # Calculate YTD metrics for hotel
    days_in_year = (today_date - year_start).days + 1
    hotel_ytd_rooms_available = hotel.total_rooms
    hotel_ytd_rooms_sold = ytd_hotel_data.aggregate(Sum('rooms_sold'))['rooms_sold__sum'] or 0
    hotel_ytd_room_revenue = ytd_hotel_data.aggregate(Sum('total_revenue'))['total_revenue__sum'] or 0
    hotel_ytd_occupancy = ytd_hotel_data.aggregate(Avg('occupancy_percentage'))['occupancy_percentage__avg'] or 0
    hotel_ytd_avg_rate = ytd_hotel_data.aggregate(Avg('average_rate'))['average_rate__avg'] or 0
    hotel_ytd_revpar = ytd_hotel_data.aggregate(Avg('revpar'))['revpar__avg'] or 0
    
    # Get YTD performance indices
    ytd_performance_indices = PerformanceIndex.objects.filter(
        hotel=hotel,
        competitor=None,  # Only get hotel's own indices
        date__gte=year_start,
        date__lte=today_date
    )
    
    # Calculate average performance indices
    daily_avg_mpi = daily_performance_indices.aggregate(Avg('mpi'))['mpi__avg'] or 0
    daily_avg_ari = daily_performance_indices.aggregate(Avg('ari'))['ari__avg'] or 0
    daily_avg_rgi = daily_performance_indices.aggregate(Avg('rgi'))['rgi__avg'] or 0
    daily_avg_fair_market_share = daily_performance_indices.aggregate(Avg('fair_market_share'))['fair_market_share__avg'] or 0
    daily_avg_actual_market_share = daily_performance_indices.aggregate(Avg('actual_market_share'))['actual_market_share__avg'] or 0
    
    mtd_avg_mpi = mtd_performance_indices.aggregate(Avg('mpi'))['mpi__avg'] or 0
    mtd_avg_ari = mtd_performance_indices.aggregate(Avg('ari'))['ari__avg'] or 0
    mtd_avg_rgi = mtd_performance_indices.aggregate(Avg('rgi'))['rgi__avg'] or 0
    mtd_avg_fair_market_share = mtd_performance_indices.aggregate(Avg('fair_market_share'))['fair_market_share__avg'] or 0
    mtd_avg_actual_market_share = mtd_performance_indices.aggregate(Avg('actual_market_share'))['actual_market_share__avg'] or 0
    
    ytd_avg_mpi = ytd_performance_indices.aggregate(Avg('mpi'))['mpi__avg'] or 0
    ytd_avg_ari = ytd_performance_indices.aggregate(Avg('ari'))['ari__avg'] or 0
    ytd_avg_rgi = ytd_performance_indices.aggregate(Avg('rgi'))['rgi__avg'] or 0
    ytd_avg_fair_market_share = ytd_performance_indices.aggregate(Avg('fair_market_share'))['fair_market_share__avg'] or 0
    ytd_avg_actual_market_share = ytd_performance_indices.aggregate(Avg('actual_market_share'))['actual_market_share__avg'] or 0
    
    # Add hotel data to the analytics dictionaries
    daily_data[hotel.name] = {
        'rooms_available': hotel_daily_rooms_available,
        'rooms_sold': hotel_daily_rooms_sold,
        'room_revenue': hotel_daily_room_revenue,
        'occupancy_percentage': hotel_daily_occupancy,
        'average_rate': hotel_daily_avg_rate,
        'revpar': hotel_daily_revpar,
        'fair_market_share': daily_avg_fair_market_share,
        'actual_market_share': daily_avg_actual_market_share,
        'mpi': daily_avg_mpi,
        'ari': daily_avg_ari,
        'rgi': daily_avg_rgi,
        'mpi_rank': 0,  # Will calculate below
        'ari_rank': 0,
        'rgi_rank': 0,
    }
    
    mtd_data[hotel.name] = {
        'rooms_available': hotel_mtd_rooms_available * days_in_month,
        'rooms_sold': hotel_mtd_rooms_sold,
        'room_revenue': hotel_mtd_room_revenue,
        'occupancy_percentage': hotel_mtd_occupancy,
        'average_rate': hotel_mtd_avg_rate,
        'revpar': hotel_mtd_revpar,
        'fair_market_share': mtd_avg_fair_market_share,
        'actual_market_share': mtd_avg_actual_market_share,
        'mpi': mtd_avg_mpi,
        'ari': mtd_avg_ari,
        'rgi': mtd_avg_rgi,
        'mpi_rank': 0,  # Will calculate below
        'ari_rank': 0,
        'rgi_rank': 0,
    }
    
    ytd_data[hotel.name] = {
        'rooms_available': hotel_ytd_rooms_available * days_in_year,
        'rooms_sold': hotel_ytd_rooms_sold,
        'room_revenue': hotel_ytd_room_revenue,
        'occupancy_percentage': hotel_ytd_occupancy,
        'average_rate': hotel_ytd_avg_rate,
        'revpar': hotel_ytd_revpar,
        'fair_market_share': ytd_avg_fair_market_share,
        'actual_market_share': ytd_avg_actual_market_share,
        'mpi': ytd_avg_mpi,
        'ari': ytd_avg_ari,
        'rgi': ytd_avg_rgi,
        'mpi_rank': 0,  # Will calculate below
        'ari_rank': 0,
        'rgi_rank': 0,
    }
    
    # Calculate metrics for each competitor and add to analytics dictionaries
    for competitor in competitors:
        # Daily metrics
        comp_daily_data = daily_competitor_data.filter(competitor=competitor)
        comp_daily_rooms_available = competitor.total_rooms
        comp_daily_rooms_sold = comp_daily_data.aggregate(Sum('rooms_sold'))['rooms_sold__sum'] or 0
        comp_daily_occupancy = comp_daily_data.aggregate(Avg('estimated_occupancy'))['estimated_occupancy__avg'] or 0
        comp_daily_avg_rate = comp_daily_data.aggregate(Avg('estimated_average_rate'))['estimated_average_rate__avg'] or 0
        
        # Calculate revenue metrics
        comp_daily_room_revenue = comp_daily_rooms_sold * comp_daily_avg_rate
        comp_daily_revpar = comp_daily_room_revenue / comp_daily_rooms_available if comp_daily_rooms_available > 0 else 0
        
        # Get competitor performance indices for the date range
        comp_daily_performance_indices = PerformanceIndex.objects.filter(
            hotel=hotel,
            competitor=competitor,
            date__gte=start_date,
            date__lte=end_date
        )
        
        # Calculate average performance indices for competitor
        comp_daily_avg_mpi = comp_daily_performance_indices.aggregate(Avg('mpi'))['mpi__avg'] or 0
        comp_daily_avg_ari = comp_daily_performance_indices.aggregate(Avg('ari'))['ari__avg'] or 0
        comp_daily_avg_rgi = comp_daily_performance_indices.aggregate(Avg('rgi'))['rgi__avg'] or 0
        comp_daily_avg_fair_market_share = comp_daily_performance_indices.aggregate(Avg('fair_market_share'))['fair_market_share__avg'] or 0
        comp_daily_avg_actual_market_share = comp_daily_performance_indices.aggregate(Avg('actual_market_share'))['actual_market_share__avg'] or 0
        
        daily_data[competitor.name] = {
            'rooms_available': comp_daily_rooms_available,
            'rooms_sold': comp_daily_rooms_sold,
            'room_revenue': comp_daily_room_revenue,
            'occupancy_percentage': comp_daily_occupancy,
            'average_rate': comp_daily_avg_rate,
            'revpar': comp_daily_revpar,
            'fair_market_share': comp_daily_avg_fair_market_share,
            'actual_market_share': comp_daily_avg_actual_market_share,
            'mpi': comp_daily_avg_mpi,
            'ari': comp_daily_avg_ari,
            'rgi': comp_daily_avg_rgi,
            'mpi_rank': 0,  # Will calculate below
            'ari_rank': 0,
            'rgi_rank': 0,
        }
        
        # MTD metrics
        comp_mtd_data = mtd_competitor_data.filter(competitor=competitor)
        comp_mtd_rooms_available = competitor.total_rooms * days_in_month
        comp_mtd_rooms_sold = comp_mtd_data.aggregate(Sum('rooms_sold'))['rooms_sold__sum'] or 0
        comp_mtd_occupancy = comp_mtd_data.aggregate(Avg('estimated_occupancy'))['estimated_occupancy__avg'] or 0
        comp_mtd_avg_rate = comp_mtd_data.aggregate(Avg('estimated_average_rate'))['estimated_average_rate__avg'] or 0
        
        # Calculate revenue metrics
        comp_mtd_room_revenue = comp_mtd_rooms_sold * comp_mtd_avg_rate
        comp_mtd_revpar = comp_mtd_room_revenue / comp_mtd_rooms_available if comp_mtd_rooms_available > 0 else 0
        
        mtd_data[competitor.name] = {
            'rooms_available': comp_mtd_rooms_available,
            'rooms_sold': comp_mtd_rooms_sold,
            'room_revenue': comp_mtd_room_revenue,
            'occupancy_percentage': comp_mtd_occupancy,
            'average_rate': comp_mtd_avg_rate,
            'revpar': comp_mtd_revpar,
            'fair_market_share': 0,  # Will calculate below
            'actual_market_share': 0,  # Will calculate below
            'mpi': 0,  # Will calculate below
            'ari': 0,  # Will calculate below
            'rgi': 0,  # Will calculate below
            'mpi_rank': 0,
            'ari_rank': 0,
            'rgi_rank': 0,
        }
        
        # YTD metrics
        comp_ytd_data = ytd_competitor_data.filter(competitor=competitor)
        comp_ytd_rooms_available = competitor.total_rooms * days_in_year
        comp_ytd_rooms_sold = comp_ytd_data.aggregate(Sum('rooms_sold'))['rooms_sold__sum'] or 0
        comp_ytd_occupancy = comp_ytd_data.aggregate(Avg('estimated_occupancy'))['estimated_occupancy__avg'] or 0
        comp_ytd_avg_rate = comp_ytd_data.aggregate(Avg('estimated_average_rate'))['estimated_average_rate__avg'] or 0
        
        # Calculate revenue metrics
        comp_ytd_room_revenue = comp_ytd_rooms_sold * comp_ytd_avg_rate
        comp_ytd_revpar = comp_ytd_room_revenue / comp_ytd_rooms_available if comp_ytd_rooms_available > 0 else 0
        
        ytd_data[competitor.name] = {
            'rooms_available': comp_ytd_rooms_available,
            'rooms_sold': comp_ytd_rooms_sold,
            'room_revenue': comp_ytd_room_revenue,
            'occupancy_percentage': comp_ytd_occupancy,
            'average_rate': comp_ytd_avg_rate,
            'revpar': comp_ytd_revpar,
            'fair_market_share': 0,  # Will calculate below
            'actual_market_share': 0,  # Will calculate below
            'mpi': 0,  # Will calculate below
            'ari': 0,  # Will calculate below
            'rgi': 0,  # Will calculate below
            'mpi_rank': 0,
            'ari_rank': 0,
            'rgi_rank': 0,
        }
    
    # Calculate totals and market shares
    # Daily totals
    daily_total_rooms_available = sum(data['rooms_available'] for data in daily_data.values())
    daily_total_rooms_sold = sum(data['rooms_sold'] for data in daily_data.values())
    daily_total_room_revenue = sum(data['room_revenue'] for data in daily_data.values())
    
    # MTD totals
    mtd_total_rooms_available = sum(data['rooms_available'] for data in mtd_data.values())
    mtd_total_rooms_sold = sum(data['rooms_sold'] for data in mtd_data.values())
    mtd_total_room_revenue = sum(data['room_revenue'] for data in mtd_data.values())
    
    # YTD totals
    ytd_total_rooms_available = sum(data['rooms_available'] for data in ytd_data.values())
    ytd_total_rooms_sold = sum(data['rooms_sold'] for data in ytd_data.values())
    ytd_total_room_revenue = sum(data['room_revenue'] for data in ytd_data.values())
    
    # Calculate totals for display - we don't need to recalculate indices since we're getting them from PerformanceIndex model
    # We only need to calculate the totals for display purposes
    
    # Calculate rankings
    # Daily rankings
    mpi_sorted = sorted(daily_data.items(), key=lambda x: x[1]['mpi'], reverse=True)
    ari_sorted = sorted(daily_data.items(), key=lambda x: x[1]['ari'], reverse=True)
    rgi_sorted = sorted(daily_data.items(), key=lambda x: x[1]['rgi'], reverse=True)
    
    for rank, (hotel_name, _) in enumerate(mpi_sorted, 1):
        daily_data[hotel_name]['mpi_rank'] = rank
    
    for rank, (hotel_name, _) in enumerate(ari_sorted, 1):
        daily_data[hotel_name]['ari_rank'] = rank
    
    for rank, (hotel_name, _) in enumerate(rgi_sorted, 1):
        daily_data[hotel_name]['rgi_rank'] = rank
    
    # MTD rankings
    mpi_sorted = sorted(mtd_data.items(), key=lambda x: x[1]['mpi'], reverse=True)
    ari_sorted = sorted(mtd_data.items(), key=lambda x: x[1]['ari'], reverse=True)
    rgi_sorted = sorted(mtd_data.items(), key=lambda x: x[1]['rgi'], reverse=True)
    
    for rank, (hotel_name, _) in enumerate(mpi_sorted, 1):
        mtd_data[hotel_name]['mpi_rank'] = rank
    
    for rank, (hotel_name, _) in enumerate(ari_sorted, 1):
        mtd_data[hotel_name]['ari_rank'] = rank
    
    for rank, (hotel_name, _) in enumerate(rgi_sorted, 1):
        mtd_data[hotel_name]['rgi_rank'] = rank
    
    # YTD rankings
    mpi_sorted = sorted(ytd_data.items(), key=lambda x: x[1]['mpi'], reverse=True)
    ari_sorted = sorted(ytd_data.items(), key=lambda x: x[1]['ari'], reverse=True)
    rgi_sorted = sorted(ytd_data.items(), key=lambda x: x[1]['rgi'], reverse=True)
    
    for rank, (hotel_name, _) in enumerate(mpi_sorted, 1):
        ytd_data[hotel_name]['mpi_rank'] = rank
    
    for rank, (hotel_name, _) in enumerate(ari_sorted, 1):
        ytd_data[hotel_name]['ari_rank'] = rank
    
    for rank, (hotel_name, _) in enumerate(rgi_sorted, 1):
        ytd_data[hotel_name]['rgi_rank'] = rank
    
    # Calculate totals for display
    daily_totals = {
        'rooms_available': daily_total_rooms_available,
        'rooms_sold': daily_total_rooms_sold,
        'room_revenue': daily_total_room_revenue,
        'occupancy_percentage': (Decimal(str(daily_total_rooms_sold)) / Decimal(str(daily_total_rooms_available)) * Decimal('100')) if daily_total_rooms_available > 0 else Decimal('0'),
        'average_rate': (Decimal(str(daily_total_room_revenue)) / Decimal(str(daily_total_rooms_sold))) if daily_total_rooms_sold > 0 else Decimal('0'),
        'revpar': (Decimal(str(daily_total_room_revenue)) / Decimal(str(daily_total_rooms_available))) if daily_total_rooms_available > 0 else Decimal('0')
    }
    
    mtd_totals = {
        'rooms_available': mtd_total_rooms_available,
        'rooms_sold': mtd_total_rooms_sold,
        'room_revenue': mtd_total_room_revenue,
        'occupancy_percentage': (Decimal(str(mtd_total_rooms_sold)) / Decimal(str(mtd_total_rooms_available)) * Decimal('100')) if mtd_total_rooms_available > 0 else Decimal('0'),
        'average_rate': (Decimal(str(mtd_total_room_revenue)) / Decimal(str(mtd_total_rooms_sold))) if mtd_total_rooms_sold > 0 else Decimal('0'),
        'revpar': (Decimal(str(mtd_total_room_revenue)) / Decimal(str(mtd_total_rooms_available))) if mtd_total_rooms_available > 0 else Decimal('0')
    }
    
    ytd_totals = {
        'rooms_available': ytd_total_rooms_available,
        'rooms_sold': ytd_total_rooms_sold,
        'room_revenue': ytd_total_room_revenue,
        'occupancy_percentage': (Decimal(str(ytd_total_rooms_sold)) / Decimal(str(ytd_total_rooms_available)) * Decimal('100')) if ytd_total_rooms_available > 0 else Decimal('0'),
        'average_rate': (Decimal(str(ytd_total_room_revenue)) / Decimal(str(ytd_total_rooms_sold))) if ytd_total_rooms_sold > 0 else Decimal('0'),
        'revpar': (Decimal(str(ytd_total_room_revenue)) / Decimal(str(ytd_total_rooms_available))) if ytd_total_rooms_available > 0 else Decimal('0')
    }
    
    # Return the data as JSON
    return JsonResponse({
        'daily_data': daily_data,
        'mtd_data': mtd_data,
        'ytd_data': ytd_data,
        'daily_totals': daily_totals,
        'mtd_totals': mtd_totals,
        'ytd_totals': ytd_totals
    })