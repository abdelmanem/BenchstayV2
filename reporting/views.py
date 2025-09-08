from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Avg, Sum, F, ExpressionWrapper, DecimalField, Count, Q
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.template.loader import get_template
import json
from datetime import timedelta, datetime
import calendar
import xlsxwriter
import io

# Import views from views_charts.py
from .views_charts import competitor_charts, competitor_analytics_charts, competitor_data_visualization

from decimal import Decimal
from .models import ReportConfiguration, SavedReport
from hotel_management.models import Hotel, Competitor, DailyData, CompetitorData, MarketSummary, PerformanceIndex
from accounts.models import UserProfile 
from xhtml2pdf import pisa
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from reportlab.lib.enums import TA_LEFT





@login_required
@permission_required('accounts.view_reporting', raise_exception=True)
def report_dashboard(request):
    """Main dashboard for reporting"""
    # Get saved reports and report configurations
    saved_reports = SavedReport.objects.all().order_by('-created_at')[:10]
    report_configs = ReportConfiguration.objects.all().order_by('-created_at')[:10]
    
    context = {
        'title': 'Reports Dashboard - Benchstay',
        'saved_reports': saved_reports,
        'report_configs': report_configs,
    }
    return render(request, 'reporting/dashboard.html', context)

@login_required
@permission_required('accounts.view_reporting', raise_exception=True)
def revenue_reports(request):
    """View for generating and viewing revenue reports"""
    hotel = Hotel.objects.first()
    
    # If no hotel exists yet, redirect to hotel data page
    if not hotel:
        messages.info(request, 'Please set up your hotel information first')
        return redirect('hotel_management:hotel_data')
    
    # Default to last 30 days
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    if request.method == 'POST':
        report_type = request.POST.get('report_type', 'daily')
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        save_report = request.POST.get('save_report') == 'on'
        report_name = request.POST.get('report_name', '')
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    # Get revenue data for the selected period
    revenue_data = DailyData.objects.filter(
        hotel=hotel,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date')
    
    # Calculate summary statistics
    summary = {
        'total_revenue': revenue_data.aggregate(Sum('total_revenue'))['total_revenue__sum'] or 0,
        'avg_daily_revenue': revenue_data.aggregate(Avg('total_revenue'))['total_revenue__avg'] or 0,
        'avg_rate': revenue_data.aggregate(Avg('average_rate'))['average_rate__avg'] or 0,
        'avg_occupancy': revenue_data.aggregate(Avg('occupancy_percentage'))['occupancy_percentage__avg'] or 0,
        'avg_revpar': revenue_data.aggregate(Avg('revpar'))['revpar__avg'] or 0,
    }
    
    context = {
        'title': 'Revenue Reports - Benchstay',
        'hotel': hotel,
        'revenue_data': revenue_data,
        'summary': summary,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'reporting/revenue_reports.html', context)

@login_required
@permission_required('accounts.view_reporting', raise_exception=True)
def occupancy_reports(request):
    """View for generating and viewing occupancy reports"""
    hotel = Hotel.objects.first()
    
    # If no hotel exists yet, redirect to hotel data page
    if not hotel:
        messages.info(request, 'Please set up your hotel information first')
        return redirect('hotel_management:hotel_data')
    
    # Default to last 30 days
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    if request.method == 'POST':
        report_type = request.POST.get('report_type', 'daily')
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        save_report = request.POST.get('save_report') == 'on'
        report_name = request.POST.get('report_name', '')
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    # Get occupancy data for the selected period
    occupancy_data = DailyData.objects.filter(
        hotel=hotel,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date')
    
    # Calculate summary statistics
    summary = {
        'avg_occupancy': occupancy_data.aggregate(Avg('occupancy_percentage'))['occupancy_percentage__avg'] or 0,
        'total_rooms_sold': occupancy_data.aggregate(Sum('rooms_sold'))['rooms_sold__sum'] or 0,
        'total_room_nights': (end_date - start_date).days * hotel.total_rooms,
        'overall_occupancy': 0,  # Will calculate below if data exists
    }
    
    # Calculate overall occupancy percentage
    if summary['total_room_nights'] > 0:
        summary['overall_occupancy'] = (summary['total_rooms_sold'] / summary['total_room_nights']) * 100
    
    context = {
        'title': 'Occupancy Reports - Benchstay',
        'hotel': hotel,
        'occupancy_data': occupancy_data,
        'summary': summary,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'reporting/occupancy_reports.html', context)

@login_required
@permission_required('accounts.view_reporting', raise_exception=True)
def competitor_analysis(request):
    """View for generating and viewing competitor analysis reports"""
    hotel = Hotel.objects.first()
    competitors = Competitor.objects.all()
    
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
    selected_competitors = competitors
    
    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        competitor_ids = request.POST.getlist('competitors')
        save_report = request.POST.get('save_report') == 'on'
        report_name = request.POST.get('report_name', '')
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        if competitor_ids:
            selected_competitors = Competitor.objects.filter(id__in=competitor_ids)
    
    # Get hotel data for the selected period
    hotel_data = DailyData.objects.filter(
        hotel=hotel,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date')
    
    # Get competitor data for the selected period and competitors
    competitor_data = CompetitorData.objects.filter(
        competitor__in=selected_competitors,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date', 'competitor__name')
    
    # Calculate summary statistics for hotel
    hotel_summary = {
        'avg_occupancy': hotel_data.aggregate(Avg('occupancy_percentage'))['occupancy_percentage__avg'] or 0,
        'avg_rate': hotel_data.aggregate(Avg('average_rate'))['average_rate__avg'] or 0,
        'avg_revpar': hotel_data.aggregate(Avg('revpar'))['revpar__avg'] or 0,
    }
    
    # Calculate summary statistics for each competitor
    competitor_summaries = {}
    for competitor in selected_competitors:
        comp_data = competitor_data.filter(competitor=competitor)
        competitor_summaries[competitor.id] = {
            'name': competitor.name,
            'avg_occupancy': comp_data.aggregate(Avg('estimated_occupancy'))['estimated_occupancy__avg'] or 0,
            'avg_rate': comp_data.aggregate(Avg('estimated_average_rate'))['estimated_average_rate__avg'] or 0,
        }
    
    context = {
        'title': 'Competitor Analysis - Benchstay',
        'hotel': hotel,
        'hotel_data': hotel_data,
        'hotel_summary': hotel_summary,
        'competitors': competitors,
        'selected_competitors': selected_competitors,
        'competitor_data': competitor_data,
        'competitor_summaries': competitor_summaries,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'reporting/competitor_analysis.html', context)

@login_required
@permission_required('accounts.view_reporting', raise_exception=True)
def competitor_advanced_analytics(request):
    """View for generating and viewing advanced competitor analytics reports"""
    hotel = Hotel.objects.first()
    competitors = Competitor.objects.all()
    
    # If no hotel exists yet, redirect to hotel data page
    if not hotel:
        messages.info(request, 'Please set up your hotel information first')
        return redirect('hotel_management:hotel_data')
    
    # If no competitors exist, redirect to competitors page
    if not competitors.exists():
        messages.info(request, 'Please add competitors first')
        return redirect('hotel_management:competitors')
    
    # Default to today
    today = timezone.now().date()
    selected_competitors = competitors
    
    # Default date range (today)
    start_date = today
    end_date = today
    
    if request.method == 'POST':
        competitor_ids = request.POST.getlist('competitors')
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        
        if competitor_ids:
            selected_competitors = Competitor.objects.filter(id__in=competitor_ids)
            
        # Process custom date range if provided
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Invalid date format. Please use YYYY-MM-DD format.')
    
    # Calculate date ranges for different periods
    today_date = today
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    
    # Get hotel data for different periods
    daily_hotel_data = DailyData.objects.filter(hotel=hotel, date__gte=start_date, date__lte=end_date)
    mtd_hotel_data = DailyData.objects.filter(hotel=hotel, date__gte=month_start, date__lte=today_date)
    ytd_hotel_data = DailyData.objects.filter(hotel=hotel, date__gte=year_start, date__lte=today_date)
    
    # Get competitor data for different periods
    daily_competitor_data = CompetitorData.objects.filter(competitor__in=selected_competitors, date__gte=start_date, date__lte=end_date)
    mtd_competitor_data = CompetitorData.objects.filter(competitor__in=selected_competitors, date__gte=month_start, date__lte=today_date)
    ytd_competitor_data = CompetitorData.objects.filter(competitor__in=selected_competitors, date__gte=year_start, date__lte=today_date)
    
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
    
    # Get hotel performance indices for the date range
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
    for competitor in selected_competitors:
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
    
    # Calculate market shares and indices
    for hotel_name in daily_data.keys():
        # Daily calculations
        daily_data[hotel_name]['fair_market_share'] = (Decimal(str(daily_data[hotel_name]['rooms_available'])) / Decimal(str(daily_total_rooms_available)) * Decimal('100')) if daily_total_rooms_available > 0 else Decimal('0')
        daily_data[hotel_name]['actual_market_share'] = (Decimal(str(daily_data[hotel_name]['rooms_sold'])) / Decimal(str(daily_total_rooms_sold)) * Decimal('100')) if daily_total_rooms_sold > 0 else Decimal('0')
        
        # Market Penetration Index (MPI)
        if daily_data[hotel_name]['fair_market_share'] > 0:
            daily_data[hotel_name]['mpi'] = daily_data[hotel_name]['actual_market_share'] / daily_data[hotel_name]['fair_market_share'] * Decimal('100')
        
        # Average Rate Index (ARI)
        daily_avg_market_rate = Decimal(str(daily_total_room_revenue)) / Decimal(str(daily_total_rooms_sold)) if daily_total_rooms_sold > 0 else Decimal('0')
        if daily_avg_market_rate > 0:
            daily_data[hotel_name]['ari'] = daily_data[hotel_name]['average_rate'] / daily_avg_market_rate * Decimal('100')
        
        # Revenue Generation Index (RGI)
        daily_market_revpar = Decimal(str(daily_total_room_revenue)) / Decimal(str(daily_total_rooms_available)) if daily_total_rooms_available > 0 else Decimal('0')
        if daily_market_revpar > 0:
            daily_data[hotel_name]['rgi'] = Decimal(str(daily_data[hotel_name]['revpar'])) / daily_market_revpar * Decimal('100')
        
        # MTD calculations
        mtd_data[hotel_name]['fair_market_share'] = (Decimal(str(mtd_data[hotel_name]['rooms_available'])) / Decimal(str(mtd_total_rooms_available)) * Decimal('100')) if mtd_total_rooms_available > 0 else Decimal('0')
        mtd_data[hotel_name]['actual_market_share'] = (Decimal(str(mtd_data[hotel_name]['rooms_sold'])) / Decimal(str(mtd_total_rooms_sold)) * Decimal('100')) if mtd_total_rooms_sold > 0 else Decimal('0')
        
        # Market Penetration Index (MPI)
        if mtd_data[hotel_name]['fair_market_share'] > 0:
            mtd_data[hotel_name]['mpi'] = mtd_data[hotel_name]['actual_market_share'] / mtd_data[hotel_name]['fair_market_share'] * Decimal('100')
        
        # Average Rate Index (ARI)
        mtd_avg_market_rate = Decimal(str(mtd_total_room_revenue)) / Decimal(str(mtd_total_rooms_sold)) if mtd_total_rooms_sold > 0 else Decimal('0')
        if mtd_avg_market_rate > 0:
            mtd_data[hotel_name]['ari'] = mtd_data[hotel_name]['average_rate'] / mtd_avg_market_rate * Decimal('100')
        
        # Revenue Generation Index (RGI)
        mtd_market_revpar = Decimal(str(mtd_total_room_revenue)) / Decimal(str(mtd_total_rooms_available)) if mtd_total_rooms_available > 0 else Decimal('0')
        if mtd_market_revpar > 0:
            mtd_data[hotel_name]['rgi'] = Decimal(str(mtd_data[hotel_name]['revpar'])) / mtd_market_revpar * Decimal('100')
        
        # YTD calculations
        ytd_data[hotel_name]['fair_market_share'] = (Decimal(str(ytd_data[hotel_name]['rooms_available'])) / Decimal(str(ytd_total_rooms_available)) * Decimal('100')) if ytd_total_rooms_available > 0 else Decimal('0')
        ytd_data[hotel_name]['actual_market_share'] = (Decimal(str(ytd_data[hotel_name]['rooms_sold'])) / Decimal(str(ytd_total_rooms_sold)) * Decimal('100')) if ytd_total_rooms_sold > 0 else Decimal('0')
        
        # Market Penetration Index (MPI)
        if ytd_data[hotel_name]['fair_market_share'] > 0:
            ytd_data[hotel_name]['mpi'] = ytd_data[hotel_name]['actual_market_share'] / ytd_data[hotel_name]['fair_market_share'] * Decimal('100')
        
        # Average Rate Index (ARI)
        ytd_avg_market_rate = Decimal(str(ytd_total_room_revenue)) / Decimal(str(ytd_total_rooms_sold)) if ytd_total_rooms_sold > 0 else Decimal('0')
        if ytd_avg_market_rate > 0:
            ytd_data[hotel_name]['ari'] = ytd_data[hotel_name]['average_rate'] / ytd_avg_market_rate * Decimal('100')
        
        # Revenue Generation Index (RGI)
        ytd_market_revpar = Decimal(str(ytd_total_room_revenue)) / Decimal(str(ytd_total_rooms_available)) if ytd_total_rooms_available > 0 else Decimal('0')
        if ytd_market_revpar > 0:
            ytd_data[hotel_name]['rgi'] = Decimal(str(ytd_data[hotel_name]['revpar'])) / ytd_market_revpar * Decimal('100')
    
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
    
    context = {
        'title': 'Advanced Competitor Analytics - Benchstay',
        'hotel': hotel,
        'competitors': competitors,
        'selected_competitors': selected_competitors,
        'analytics_data': True,  # Flag to show analytics sections
        'daily_data': daily_data,
        'mtd_data': mtd_data,
        'ytd_data': ytd_data,
        # JSON versions for client-side scripts
        'daily_data_json': json.dumps(daily_data, default=str),
        'mtd_data_json': json.dumps(mtd_data, default=str),
        'ytd_data_json': json.dumps(ytd_data, default=str),
        'daily_totals': daily_totals,
        'mtd_totals': mtd_totals,
        'ytd_totals': ytd_totals,
        'start_date': start_date,
        'end_date': end_date
    }
    
    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'daily_data': daily_data,
            'mtd_data': mtd_data,
            'ytd_data': ytd_data,
        })
    
    return render(request, 'reporting/competitor_advanced_analytics.html', context)

def export_competitor_analytics_pdf(request, hotel_id):
    """Generate PDF using the same logic as competitor_advanced_analytics view"""
    
    # Get hotel and competitors (same as your existing view)
    hotel = get_object_or_404(Hotel, id=hotel_id)
    competitors = Competitor.objects.all()
    
    # Get date parameters
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    competitor_ids = request.GET.getlist('competitors')
    
    # Default to today if no dates provided
    today = timezone.now().date()
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else today
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else today
    except ValueError:
        start_date = today
        end_date = today
    
    # Filter competitors if specific ones are selected
    if competitor_ids:
        selected_competitors = Competitor.objects.filter(id__in=competitor_ids)
    else:
        selected_competitors = competitors
    
    # Calculate date ranges for different periods (same as your view)
    today_date = today
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    
    # Get hotel data for different periods (same as your view)
    daily_hotel_data = DailyData.objects.filter(hotel=hotel, date__gte=start_date, date__lte=end_date)
    mtd_hotel_data = DailyData.objects.filter(hotel=hotel, date__gte=month_start, date__lte=today_date)
    ytd_hotel_data = DailyData.objects.filter(hotel=hotel, date__gte=year_start, date__lte=today_date)
    
    # Get competitor data for different periods (same as your view)
    daily_competitor_data = CompetitorData.objects.filter(competitor__in=selected_competitors, date__gte=start_date, date__lte=end_date)
    mtd_competitor_data = CompetitorData.objects.filter(competitor__in=selected_competitors, date__gte=month_start, date__lte=today_date)
    ytd_competitor_data = CompetitorData.objects.filter(competitor__in=selected_competitors, date__gte=year_start, date__lte=today_date)
    
    # Initialize data structures (same as your view)
    daily_data = {}
    mtd_data = {}
    ytd_data = {}
    
    # HOTEL DATA CALCULATIONS (copied from your view)
    # Calculate daily metrics for hotel
    hotel_daily_rooms_available = hotel.total_rooms
    hotel_daily_rooms_sold = daily_hotel_data.aggregate(Sum('rooms_sold'))['rooms_sold__sum'] or 0
    hotel_daily_room_revenue = daily_hotel_data.aggregate(Sum('total_revenue'))['total_revenue__sum'] or 0
    hotel_daily_occupancy = daily_hotel_data.aggregate(Avg('occupancy_percentage'))['occupancy_percentage__avg'] or 0
    hotel_daily_avg_rate = daily_hotel_data.aggregate(Avg('average_rate'))['average_rate__avg'] or 0
    hotel_daily_revpar = daily_hotel_data.aggregate(Avg('revpar'))['revpar__avg'] or 0
    
    # Calculate MTD metrics for hotel
    days_in_month = (today_date - month_start).days + 1
    hotel_mtd_rooms_available = hotel.total_rooms
    hotel_mtd_rooms_sold = mtd_hotel_data.aggregate(Sum('rooms_sold'))['rooms_sold__sum'] or 0
    hotel_mtd_room_revenue = mtd_hotel_data.aggregate(Sum('total_revenue'))['total_revenue__sum'] or 0
    hotel_mtd_occupancy = mtd_hotel_data.aggregate(Avg('occupancy_percentage'))['occupancy_percentage__avg'] or 0
    hotel_mtd_avg_rate = mtd_hotel_data.aggregate(Avg('average_rate'))['average_rate__avg'] or 0
    hotel_mtd_revpar = mtd_hotel_data.aggregate(Avg('revpar'))['revpar__avg'] or 0
    
    # Calculate YTD metrics for hotel
    days_in_year = (today_date - year_start).days + 1
    hotel_ytd_rooms_available = hotel.total_rooms
    hotel_ytd_rooms_sold = ytd_hotel_data.aggregate(Sum('rooms_sold'))['rooms_sold__sum'] or 0
    hotel_ytd_room_revenue = ytd_hotel_data.aggregate(Sum('total_revenue'))['total_revenue__sum'] or 0
    hotel_ytd_occupancy = ytd_hotel_data.aggregate(Avg('occupancy_percentage'))['occupancy_percentage__avg'] or 0
    hotel_ytd_avg_rate = ytd_hotel_data.aggregate(Avg('average_rate'))['average_rate__avg'] or 0
    hotel_ytd_revpar = ytd_hotel_data.aggregate(Avg('revpar'))['revpar__avg'] or 0
    
    # Get performance indices (simplified version - you can enhance this)
    daily_performance_indices = PerformanceIndex.objects.filter(
        hotel=hotel, competitor=None, date__gte=start_date, date__lte=end_date
    )
    mtd_performance_indices = PerformanceIndex.objects.filter(
        hotel=hotel, competitor=None, date__gte=month_start, date__lte=today_date
    )
    ytd_performance_indices = PerformanceIndex.objects.filter(
        hotel=hotel, competitor=None, date__gte=year_start, date__lte=today_date
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
    
    # Add hotel data to the analytics dictionaries (same as your view)
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
        'mpi_rank': 0,
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
        'mpi_rank': 0,
        'ari_rank': 0,
        'rgi_rank': 0,
    }
    
    # COMPETITOR DATA CALCULATIONS (copied from your view)
    for competitor in selected_competitors:
        # Daily metrics
        comp_daily_data = daily_competitor_data.filter(competitor=competitor)
        comp_daily_rooms_available = competitor.total_rooms
        comp_daily_rooms_sold = comp_daily_data.aggregate(Sum('rooms_sold'))['rooms_sold__sum'] or 0
        comp_daily_occupancy = comp_daily_data.aggregate(Avg('estimated_occupancy'))['estimated_occupancy__avg'] or 0
        comp_daily_avg_rate = comp_daily_data.aggregate(Avg('estimated_average_rate'))['estimated_average_rate__avg'] or 0
        
        # Calculate revenue metrics
        comp_daily_room_revenue = comp_daily_rooms_sold * comp_daily_avg_rate
        comp_daily_revpar = comp_daily_room_revenue / comp_daily_rooms_available if comp_daily_rooms_available > 0 else 0
        
        # Get competitor performance indices
        comp_daily_performance_indices = PerformanceIndex.objects.filter(
            hotel=hotel, competitor=competitor, date__gte=start_date, date__lte=end_date
        )
        
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
            'mpi_rank': 0,
            'ari_rank': 0,
            'rgi_rank': 0,
        }
        
        # MTD metrics
        comp_mtd_data = mtd_competitor_data.filter(competitor=competitor)
        comp_mtd_rooms_available = competitor.total_rooms * days_in_month
        comp_mtd_rooms_sold = comp_mtd_data.aggregate(Sum('rooms_sold'))['rooms_sold__sum'] or 0
        comp_mtd_occupancy = comp_mtd_data.aggregate(Avg('estimated_occupancy'))['estimated_occupancy__avg'] or 0
        comp_mtd_avg_rate = comp_mtd_data.aggregate(Avg('estimated_average_rate'))['estimated_average_rate__avg'] or 0
        
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
            'actual_market_share': 0,
            'mpi': 0,
            'ari': 0,
            'rgi': 0,
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
        
        comp_ytd_room_revenue = comp_ytd_rooms_sold * comp_ytd_avg_rate
        comp_ytd_revpar = comp_ytd_room_revenue / comp_ytd_rooms_available if comp_ytd_rooms_available > 0 else 0
        
        ytd_data[competitor.name] = {
            'rooms_available': comp_ytd_rooms_available,
            'rooms_sold': comp_ytd_rooms_sold,
            'room_revenue': comp_ytd_room_revenue,
            'occupancy_percentage': comp_ytd_occupancy,
            'average_rate': comp_ytd_avg_rate,
            'revpar': comp_ytd_revpar,
            'fair_market_share': 0,
            'actual_market_share': 0,
            'mpi': 0,
            'ari': 0,
            'rgi': 0,
            'mpi_rank': 0,
            'ari_rank': 0,
            'rgi_rank': 0,
        }
    
    # MARKET SHARE CALCULATIONS (copied from your view)
    # Calculate totals
    daily_total_rooms_available = sum(data['rooms_available'] for data in daily_data.values())
    daily_total_rooms_sold = sum(data['rooms_sold'] for data in daily_data.values())
    daily_total_room_revenue = sum(data['room_revenue'] for data in daily_data.values())
    
    mtd_total_rooms_available = sum(data['rooms_available'] for data in mtd_data.values())
    mtd_total_rooms_sold = sum(data['rooms_sold'] for data in mtd_data.values())
    mtd_total_room_revenue = sum(data['room_revenue'] for data in mtd_data.values())
    
    ytd_total_rooms_available = sum(data['rooms_available'] for data in ytd_data.values())
    ytd_total_rooms_sold = sum(data['rooms_sold'] for data in ytd_data.values())
    ytd_total_room_revenue = sum(data['room_revenue'] for data in ytd_data.values())
    
    # Calculate market shares and indices (simplified version of your complex logic)
    for hotel_name in daily_data.keys():
        # Daily calculations
        if daily_total_rooms_available > 0:
            daily_data[hotel_name]['fair_market_share'] = float(daily_data[hotel_name]['rooms_available'] / daily_total_rooms_available * 100)
        if daily_total_rooms_sold > 0:
            daily_data[hotel_name]['actual_market_share'] = float(daily_data[hotel_name]['rooms_sold'] / daily_total_rooms_sold * 100)
        
        # MTD calculations
        if mtd_total_rooms_available > 0:
            mtd_data[hotel_name]['fair_market_share'] = float(mtd_data[hotel_name]['rooms_available'] / mtd_total_rooms_available * 100)
        if mtd_total_rooms_sold > 0:
            mtd_data[hotel_name]['actual_market_share'] = float(mtd_data[hotel_name]['rooms_sold'] / mtd_total_rooms_sold * 100)
        
        # YTD calculations
        if ytd_total_rooms_available > 0:
            ytd_data[hotel_name]['fair_market_share'] = float(ytd_data[hotel_name]['rooms_available'] / ytd_total_rooms_available * 100)
        if ytd_total_rooms_sold > 0:
            ytd_data[hotel_name]['actual_market_share'] = float(ytd_data[hotel_name]['rooms_sold'] / ytd_total_rooms_sold * 100)
    
    # RANKINGS (copied from your view)
    def calculate_rankings(data_dict):
        """Calculate rankings for MPI, ARI, RGI"""
        # MPI rankings
        mpi_sorted = sorted(data_dict.items(), key=lambda x: x[1]['mpi'], reverse=True)
        for rank, (hotel_name, _) in enumerate(mpi_sorted, 1):
            data_dict[hotel_name]['mpi_rank'] = rank
        
        # ARI rankings
        ari_sorted = sorted(data_dict.items(), key=lambda x: x[1]['ari'], reverse=True)
        for rank, (hotel_name, _) in enumerate(ari_sorted, 1):
            data_dict[hotel_name]['ari_rank'] = rank
        
        # RGI rankings
        rgi_sorted = sorted(data_dict.items(), key=lambda x: x[1]['rgi'], reverse=True)
        for rank, (hotel_name, _) in enumerate(rgi_sorted, 1):
            data_dict[hotel_name]['rgi_rank'] = rank
    
    # Calculate rankings for all periods
    calculate_rankings(daily_data)
    calculate_rankings(mtd_data)
    calculate_rankings(ytd_data)
    
    # DEBUG: Print data to verify
    print(f"Daily data hotels: {list(daily_data.keys())}")
    print(f"MTD data hotels: {list(mtd_data.keys())}")
    print(f"YTD data hotels: {list(ytd_data.keys())}")
    
    # NOW CREATE THE PDF (using the same PDF generation code from before)
    # Create PDF buffer
    buffer = BytesIO()
    
    # Create PDF document with landscape A3
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A3),
        rightMargin=10*mm,
        leftMargin=10*mm,
        topMargin=20*mm,
        bottomMargin=15*mm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=6*mm,
        alignment=TA_LEFT
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        fontSize=12,
        textColor=colors.HexColor('#646464'),
        spaceAfter=2*mm,
        alignment=TA_LEFT
    )
    
    # Build PDF content
    story = []
    
    # Header
    title = Paragraph(f"{hotel.name} - Market Share Report", title_style)
    story.append(title)
    
    date_range = Paragraph(
        f"Date Range: {start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}", 
        subtitle_style
    )
    story.append(date_range)
    
    generated_date = Paragraph(
        f"Generated on: {datetime.now().strftime('%m/%d/%Y')}", 
        subtitle_style
    )
    story.append(generated_date)
    
    story.append(Spacer(1, 10*mm))
    
    # Table configurations (only selected date range to match on-screen report)
    table_configs = [
        {
            'data': daily_data,
            'title': 'Custom Date Range Performance Metrics',
            'color': colors.HexColor('#d97706'),
        }
    ]
    
    def create_performance_table(data, title, header_color):
        """Create table with actual data"""
        
        if not data or len(data) == 0:
            section_style = ParagraphStyle(
                'SectionTitle',
                fontSize=14,
                textColor=header_color,
                spaceAfter=8*mm,
                spaceBefore=15*mm,
                alignment=TA_LEFT,
                fontName='Helvetica-Bold'
            )
            story.append(Paragraph(title, section_style))
            story.append(Paragraph("No data available for this period.", styles['Normal']))
            story.append(Spacer(1, 15*mm))
            return
        
        section_style = ParagraphStyle(
            'SectionTitle',
            fontSize=14,
            textColor=header_color,
            spaceAfter=8*mm,
            spaceBefore=15*mm,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        )
        story.append(Paragraph(title, section_style))
        
        # Table headers
        headers = [
            'Hotel', 'Total\nRooms', 'Occupancy\n%', 'Avg Rate', 
            'Sold\nRooms', 'Room Revenue', 'RevPAR', 'Fair Market\nShare',
            'Actual Market\nShare', 'MPI\nRank', 'MPI\nIndex', 
            'ARI\nRank', 'ARI\nIndex', 'RGI\nRank', 'RGI\nIndex'
        ]
        
        table_data = [headers]
        
        for hotel_name, metrics in data.items():
            row = [
                hotel_name,
                str(int(metrics.get('rooms_available', 0))),
                f"{float(metrics.get('occupancy_percentage', 0)):.1f}%",
                f"EGP {float(metrics.get('average_rate', 0)):.2f}",
                str(int(metrics.get('rooms_sold', 0))),
                f"EGP {float(metrics.get('room_revenue', 0)):.2f}",
                f"EGP {float(metrics.get('revpar', 0)):.2f}",
                f"{float(metrics.get('fair_market_share', 0)):.2f}%",
                f"{float(metrics.get('actual_market_share', 0)):.2f}%",
                str(metrics.get('mpi_rank', '-')),
                f"{float(metrics.get('mpi', 0)):.2f}",
                str(metrics.get('ari_rank', '-')),
                f"{float(metrics.get('ari', 0)):.2f}",
                str(metrics.get('rgi_rank', '-')),
                f"{float(metrics.get('rgi', 0)):.2f}",
            ]
            table_data.append(row)
        
        # Column widths
        col_widths = [
            35*mm, 20*mm, 18*mm, 22*mm, 18*mm, 25*mm, 22*mm, 20*mm,
            20*mm, 15*mm, 18*mm, 15*mm, 18*mm, 15*mm, 18*mm
        ]
        
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Table styling
        table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), header_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 2*mm),
            ('TOPPADDING', (0, 0), (-1, 0), 2*mm),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.1*mm, colors.HexColor('#c8c8c8')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 2*mm),
            ('TOPPADDING', (0, 1), (-1, -1), 2*mm),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ]
        
        table.setStyle(TableStyle(table_style))
        story.append(table)
        story.append(Spacer(1, 15*mm))
    
    # Add all tables
    for config in table_configs:
        create_performance_table(
            config['data'], 
            config['title'], 
            config['color']
        )
    
    # Build PDF
    doc.build(story)
    
    # Return PDF response
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    
    filename = f"{hotel.name.replace(' ', '_')}_Market_Report_{start_date.strftime('%Y-%m-%d')}_to_{end_date.strftime('%Y-%m-%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response
# Removed unused WeasyPrint export function that referenced undefined variables


def calculate_daily_metrics(hotel, competitors, start_date, end_date):
    """Calculate daily metrics for hotel and competitors"""
    # Get hotel data for the selected period
    daily_hotel_data = DailyData.objects.filter(
        hotel=hotel,
        date__gte=start_date,
        date__lte=end_date
    )
    
    # Get competitor data for the selected period
    daily_competitor_data = CompetitorData.objects.filter(
        competitor__in=competitors,
        date__gte=start_date,
        date__lte=end_date
    )
    
    # Initialize data dictionary
    daily_data = {}
    
    # Calculate hotel metrics
    hotel_daily_rooms_available = hotel.total_rooms
    hotel_daily_rooms_sold = daily_hotel_data.aggregate(Sum('rooms_sold'))['rooms_sold__sum'] or 0
    hotel_daily_room_revenue = daily_hotel_data.aggregate(Sum('total_revenue'))['total_revenue__sum'] or 0
    hotel_daily_occupancy = daily_hotel_data.aggregate(Avg('occupancy_percentage'))['occupancy_percentage__avg'] or 0
    hotel_daily_avg_rate = daily_hotel_data.aggregate(Avg('average_rate'))['average_rate__avg'] or 0
    hotel_daily_revpar = daily_hotel_data.aggregate(Avg('revpar'))['revpar__avg'] or 0
    
    # Get hotel performance indices
    daily_performance_indices = PerformanceIndex.objects.filter(
        hotel=hotel,
        competitor=None,
        date__gte=start_date,
        date__lte=end_date
    )
    
    daily_avg_mpi = daily_performance_indices.aggregate(Avg('mpi'))['mpi__avg'] or 0
    daily_avg_ari = daily_performance_indices.aggregate(Avg('ari'))['ari__avg'] or 0
    daily_avg_rgi = daily_performance_indices.aggregate(Avg('rgi'))['rgi__avg'] or 0
    daily_avg_fair_market_share = daily_performance_indices.aggregate(Avg('fair_market_share'))['fair_market_share__avg'] or 0
    daily_avg_actual_market_share = daily_performance_indices.aggregate(Avg('actual_market_share'))['actual_market_share__avg'] or 0
    
    # Add hotel data
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
        'mpi_rank': 0,
        'ari_rank': 0,
        'rgi_rank': 0
    }
    
    # Calculate metrics for each competitor
    for competitor in competitors:
        comp_daily_data = daily_competitor_data.filter(competitor=competitor)
        comp_daily_rooms_available = competitor.total_rooms
        comp_daily_rooms_sold = comp_daily_data.aggregate(Sum('rooms_sold'))['rooms_sold__sum'] or 0
        comp_daily_occupancy = comp_daily_data.aggregate(Avg('estimated_occupancy'))['estimated_occupancy__avg'] or 0
        comp_daily_avg_rate = comp_daily_data.aggregate(Avg('estimated_average_rate'))['estimated_average_rate__avg'] or 0
        
        # Calculate revenue metrics
        comp_daily_room_revenue = comp_daily_rooms_sold * comp_daily_avg_rate
        comp_daily_revpar = comp_daily_room_revenue / comp_daily_rooms_available if comp_daily_rooms_available > 0 else 0
        
        # Get competitor performance indices
        comp_performance_indices = PerformanceIndex.objects.filter(
            hotel=hotel,
            competitor=competitor,
            date__gte=start_date,
            date__lte=end_date
        )
        
        comp_avg_mpi = comp_performance_indices.aggregate(Avg('mpi'))['mpi__avg'] or 0
        comp_avg_ari = comp_performance_indices.aggregate(Avg('ari'))['ari__avg'] or 0
        comp_avg_rgi = comp_performance_indices.aggregate(Avg('rgi'))['rgi__avg'] or 0
        comp_avg_fair_market_share = comp_performance_indices.aggregate(Avg('fair_market_share'))['fair_market_share__avg'] or 0
        comp_avg_actual_market_share = comp_performance_indices.aggregate(Avg('actual_market_share'))['actual_market_share__avg'] or 0
        
        daily_data[competitor.name] = {
            'rooms_available': comp_daily_rooms_available,
            'rooms_sold': comp_daily_rooms_sold,
            'room_revenue': comp_daily_room_revenue,
            'occupancy_percentage': comp_daily_occupancy,
            'average_rate': comp_daily_avg_rate,
            'revpar': comp_daily_revpar,
            'fair_market_share': comp_avg_fair_market_share,
            'actual_market_share': comp_avg_actual_market_share,
            'mpi': comp_avg_mpi,
            'ari': comp_avg_ari,
            'rgi': comp_avg_rgi,
            'mpi_rank': 0,
            'ari_rank': 0,
            'rgi_rank': 0
        }
    
    # Calculate totals
    daily_total_rooms_available = sum(data['rooms_available'] for data in daily_data.values())
    daily_total_rooms_sold = sum(data['rooms_sold'] for data in daily_data.values())
    daily_total_room_revenue = sum(data['room_revenue'] for data in daily_data.values())
    
    # Calculate market averages
    daily_market_occupancy = (daily_total_rooms_sold / daily_total_rooms_available * 100) if daily_total_rooms_available > 0 else 0
    daily_market_avg_rate = (daily_total_room_revenue / daily_total_rooms_sold) if daily_total_rooms_sold > 0 else 0
    daily_market_revpar = (daily_total_room_revenue / daily_total_rooms_available) if daily_total_rooms_available > 0 else 0
    
    daily_totals = {
        'rooms_available': daily_total_rooms_available,
        'rooms_sold': daily_total_rooms_sold,
        'room_revenue': daily_total_room_revenue,
        'occupancy_percentage': daily_market_occupancy,
        'average_rate': daily_market_avg_rate,
        'revpar': daily_market_revpar
    }
    
    return daily_data, daily_totals

@login_required
def calculate_ytd_metrics(hotel, competitors):
    """Calculate year-to-date metrics for hotel and competitors"""
    # Get current date and start of year
    today = timezone.now().date()
    year_start = today.replace(month=1, day=1)
    
    # Get hotel data for the year-to-date period
    ytd_hotel_data = DailyData.objects.filter(
        hotel=hotel,
        date__gte=year_start,
        date__lte=today
    )
    
    # Get competitor data for the year-to-date period
    ytd_competitor_data = CompetitorData.objects.filter(
        competitor__in=competitors,
        date__gte=year_start,
        date__lte=today
    )
    
    # Initialize data dictionary
    ytd_data = {}
    
    # Calculate days in year so far
    days_in_year = (today - year_start).days + 1
    
    # Calculate hotel metrics
    hotel_ytd_rooms_available = hotel.total_rooms * days_in_year
    hotel_ytd_rooms_sold = ytd_hotel_data.aggregate(Sum('rooms_sold'))['rooms_sold__sum'] or 0
    hotel_ytd_room_revenue = ytd_hotel_data.aggregate(Sum('total_revenue'))['total_revenue__sum'] or 0
    hotel_ytd_occupancy = ytd_hotel_data.aggregate(Avg('occupancy_percentage'))['occupancy_percentage__avg'] or 0
    hotel_ytd_avg_rate = ytd_hotel_data.aggregate(Avg('average_rate'))['average_rate__avg'] or 0
    hotel_ytd_revpar = ytd_hotel_data.aggregate(Avg('revpar'))['revpar__avg'] or 0
    
    # Get hotel performance indices
    ytd_performance_indices = PerformanceIndex.objects.filter(
        hotel=hotel,
        competitor=None,
        date__gte=year_start,
        date__lte=today
    )
    
    ytd_avg_mpi = ytd_performance_indices.aggregate(Avg('mpi'))['mpi__avg'] or 0
    ytd_avg_ari = ytd_performance_indices.aggregate(Avg('ari'))['ari__avg'] or 0
    ytd_avg_rgi = ytd_performance_indices.aggregate(Avg('rgi'))['rgi__avg'] or 0
    ytd_avg_fair_market_share = ytd_performance_indices.aggregate(Avg('fair_market_share'))['fair_market_share__avg'] or 0
    ytd_avg_actual_market_share = ytd_performance_indices.aggregate(Avg('actual_market_share'))['actual_market_share__avg'] or 0
    
    # Add hotel data
    ytd_data[hotel.name] = {
        'rooms_available': hotel_ytd_rooms_available,
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
        'mpi_rank': 0,
        'ari_rank': 0,
        'rgi_rank': 0
    }
    
    # Calculate metrics for each competitor
    for competitor in competitors:
        comp_ytd_data = ytd_competitor_data.filter(competitor=competitor)
        comp_ytd_rooms_available = competitor.total_rooms * days_in_year
        comp_ytd_rooms_sold = comp_ytd_data.aggregate(Sum('rooms_sold'))['rooms_sold__sum'] or 0
        comp_ytd_occupancy = comp_ytd_data.aggregate(Avg('estimated_occupancy'))['estimated_occupancy__avg'] or 0
        comp_ytd_avg_rate = comp_ytd_data.aggregate(Avg('estimated_average_rate'))['estimated_average_rate__avg'] or 0
        
        # Calculate revenue metrics
        comp_ytd_room_revenue = comp_ytd_rooms_sold * comp_ytd_avg_rate
        comp_ytd_revpar = comp_ytd_room_revenue / comp_ytd_rooms_available if comp_ytd_rooms_available > 0 else 0
        
        # Get competitor performance indices
        comp_performance_indices = PerformanceIndex.objects.filter(
            hotel=hotel,
            competitor=competitor,
            date__gte=year_start,
            date__lte=today
        )
        
        comp_avg_mpi = comp_performance_indices.aggregate(Avg('mpi'))['mpi__avg'] or 0
        comp_avg_ari = comp_performance_indices.aggregate(Avg('ari'))['ari__avg'] or 0
        comp_avg_rgi = comp_performance_indices.aggregate(Avg('rgi'))['rgi__avg'] or 0
        comp_avg_fair_market_share = comp_performance_indices.aggregate(Avg('fair_market_share'))['fair_market_share__avg'] or 0
        comp_avg_actual_market_share = comp_performance_indices.aggregate(Avg('actual_market_share'))['actual_market_share__avg'] or 0
        
        ytd_data[competitor.name] = {
            'rooms_available': comp_ytd_rooms_available,
            'rooms_sold': comp_ytd_rooms_sold,
            'room_revenue': comp_ytd_room_revenue,
            'occupancy_percentage': comp_ytd_occupancy,
            'average_rate': comp_ytd_avg_rate,
            'revpar': comp_ytd_revpar,
            'fair_market_share': comp_avg_fair_market_share,
            'actual_market_share': comp_avg_actual_market_share,
            'mpi': comp_avg_mpi,
            'ari': comp_avg_ari,
            'rgi': comp_avg_rgi,
            'mpi_rank': 0,
            'ari_rank': 0,
            'rgi_rank': 0
        }
    
    # Calculate totals
    ytd_total_rooms_available = sum(data['rooms_available'] for data in ytd_data.values())
    ytd_total_rooms_sold = sum(data['rooms_sold'] for data in ytd_data.values())
    ytd_total_room_revenue = sum(data['room_revenue'] for data in ytd_data.values())
    
    # Calculate market averages
    ytd_market_occupancy = (ytd_total_rooms_sold / ytd_total_rooms_available * 100) if ytd_total_rooms_available > 0 else 0
    ytd_market_avg_rate = (ytd_total_room_revenue / ytd_total_rooms_sold) if ytd_total_rooms_sold > 0 else 0
    ytd_market_revpar = (ytd_total_room_revenue / ytd_total_rooms_available) if ytd_total_rooms_available > 0 else 0
    
    ytd_totals = {
        'rooms_available': ytd_total_rooms_available,
        'rooms_sold': ytd_total_rooms_sold,
        'room_revenue': ytd_total_room_revenue,
        'occupancy_percentage': ytd_market_occupancy,
        'average_rate': ytd_market_avg_rate,
        'revpar': ytd_market_revpar
    }
    
    return ytd_data, ytd_totals

@login_required
def calculate_mtd_metrics(hotel, competitors):
    """Calculate month-to-date metrics for hotel and competitors"""
    # Get current date and start of month
    today = timezone.now().date()
    month_start = today.replace(day=1)
    
    # Get hotel data for the month-to-date period
    mtd_hotel_data = DailyData.objects.filter(
        hotel=hotel,
        date__gte=month_start,
        date__lte=today
    )
    
    # Get competitor data for the month-to-date period
    mtd_competitor_data = CompetitorData.objects.filter(
        competitor__in=competitors,
        date__gte=month_start,
        date__lte=today
    )
    
    # Initialize data dictionary
    mtd_data = {}
    
    # Calculate days in month so far
    days_in_month = (today - month_start).days + 1
    
    # Calculate hotel metrics
    hotel_mtd_rooms_available = hotel.total_rooms * days_in_month
    hotel_mtd_rooms_sold = mtd_hotel_data.aggregate(Sum('rooms_sold'))['rooms_sold__sum'] or 0
    hotel_mtd_room_revenue = mtd_hotel_data.aggregate(Sum('total_revenue'))['total_revenue__sum'] or 0
    hotel_mtd_occupancy = mtd_hotel_data.aggregate(Avg('occupancy_percentage'))['occupancy_percentage__avg'] or 0
    hotel_mtd_avg_rate = mtd_hotel_data.aggregate(Avg('average_rate'))['average_rate__avg'] or 0
    hotel_mtd_revpar = mtd_hotel_data.aggregate(Avg('revpar'))['revpar__avg'] or 0
    
    # Get hotel performance indices
    mtd_performance_indices = PerformanceIndex.objects.filter(
        hotel=hotel,
        competitor=None,
        date__gte=month_start,
        date__lte=today
    )
    
    mtd_avg_mpi = mtd_performance_indices.aggregate(Avg('mpi'))['mpi__avg'] or 0
    mtd_avg_ari = mtd_performance_indices.aggregate(Avg('ari'))['ari__avg'] or 0
    mtd_avg_rgi = mtd_performance_indices.aggregate(Avg('rgi'))['rgi__avg'] or 0
    mtd_avg_fair_market_share = mtd_performance_indices.aggregate(Avg('fair_market_share'))['fair_market_share__avg'] or 0
    mtd_avg_actual_market_share = mtd_performance_indices.aggregate(Avg('actual_market_share'))['actual_market_share__avg'] or 0
    
    # Add hotel data
    mtd_data[hotel.name] = {
        'rooms_available': hotel_mtd_rooms_available,
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
        'mpi_rank': 0,
        'ari_rank': 0,
        'rgi_rank': 0
    }
    
    # Calculate metrics for each competitor
    for competitor in competitors:
        comp_mtd_data = mtd_competitor_data.filter(competitor=competitor)
        comp_mtd_rooms_available = competitor.total_rooms * days_in_month
        comp_mtd_rooms_sold = comp_mtd_data.aggregate(Sum('rooms_sold'))['rooms_sold__sum'] or 0
        comp_mtd_occupancy = comp_mtd_data.aggregate(Avg('estimated_occupancy'))['estimated_occupancy__avg'] or 0
        comp_mtd_avg_rate = comp_mtd_data.aggregate(Avg('estimated_average_rate'))['estimated_average_rate__avg'] or 0
        
        # Calculate revenue metrics
        comp_mtd_room_revenue = comp_mtd_rooms_sold * comp_mtd_avg_rate
        comp_mtd_revpar = comp_mtd_room_revenue / comp_mtd_rooms_available if comp_mtd_rooms_available > 0 else 0
        
        # Get competitor performance indices
        comp_performance_indices = PerformanceIndex.objects.filter(
            hotel=hotel,
            competitor=competitor,
            date__gte=month_start,
            date__lte=today
        )
        
        comp_avg_mpi = comp_performance_indices.aggregate(Avg('mpi'))['mpi__avg'] or 0
        comp_avg_ari = comp_performance_indices.aggregate(Avg('ari'))['ari__avg'] or 0
        comp_avg_rgi = comp_performance_indices.aggregate(Avg('rgi'))['rgi__avg'] or 0
        comp_avg_fair_market_share = comp_performance_indices.aggregate(Avg('fair_market_share'))['fair_market_share__avg'] or 0
        comp_avg_actual_market_share = comp_performance_indices.aggregate(Avg('actual_market_share'))['actual_market_share__avg'] or 0
        
        mtd_data[competitor.name] = {
            'rooms_available': comp_mtd_rooms_available,
            'rooms_sold': comp_mtd_rooms_sold,
            'room_revenue': comp_mtd_room_revenue,
            'occupancy_percentage': comp_mtd_occupancy,
            'average_rate': comp_mtd_avg_rate,
            'revpar': comp_mtd_revpar,
            'fair_market_share': comp_avg_fair_market_share,
            'actual_market_share': comp_avg_actual_market_share,
            'mpi': comp_avg_mpi,
            'ari': comp_avg_ari,
            'rgi': comp_avg_rgi,
            'mpi_rank': 0,
            'ari_rank': 0,
            'rgi_rank': 0
        }
    
    # Calculate totals
    mtd_total_rooms_available = sum(data['rooms_available'] for data in mtd_data.values())
    mtd_total_rooms_sold = sum(data['rooms_sold'] for data in mtd_data.values())
    mtd_total_room_revenue = sum(data['room_revenue'] for data in mtd_data.values())
    
    # Calculate market averages
    mtd_market_occupancy = (mtd_total_rooms_sold / mtd_total_rooms_available * 100) if mtd_total_rooms_available > 0 else 0
    mtd_market_avg_rate = (mtd_total_room_revenue / mtd_total_rooms_sold) if mtd_total_rooms_sold > 0 else 0
    mtd_market_revpar = (mtd_total_room_revenue / mtd_total_rooms_available) if mtd_total_rooms_available > 0 else 0
    
    mtd_totals = {
        'rooms_available': mtd_total_rooms_available,
        'rooms_sold': mtd_total_rooms_sold,
        'room_revenue': mtd_total_room_revenue,
        'occupancy_percentage': mtd_market_occupancy,
        'average_rate': mtd_market_avg_rate,
        'revpar': mtd_market_revpar
    }
    
    return mtd_data, mtd_totals

# @login_required
# def export_competitor_analytics(request):
    """Export competitor analytics data to PDF or Excel format"""
    # try:
    #     # Check if user has admin profile
    #     if not request.user.profile.is_admin:
    #         return HttpResponseForbidden('You do not have permission to access this page')
    # except UserProfile.DoesNotExist:
    #     return HttpResponseForbidden('You do not have permission to access this page. User profile not found.')
    # except Exception as e:
    #     return HttpResponseForbidden(f'Error checking permissions: {str(e)}')
        
@login_required
def export_competitor_analytics(request):
    """Export competitor analytics data to PDF or Excel format"""
    format_type = request.GET.get('format', 'pdf')
    date_range = request.GET.get('date_range', 'this_month')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    specific_date = request.GET.get('specific_date')
    competitor_ids = request.GET.getlist('competitors')
    
    # Define today's date
    today = timezone.now().date()
    
    # Convert string dates to date objects if provided
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = today
            
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            end_date = today
    except ValueError:
        # If date parsing fails, use today's date
        start_date = today
        end_date = today
    
    # Initialize variables
    daily_data = {}
    mtd_data = {}
    ytd_data = {}
    daily_totals = {}
    mtd_totals = {}
    ytd_totals = {}
    
    # Get hotel and competitor data
    try:
        hotel = Hotel.objects.first()
        if not hotel:
            return HttpResponseForbidden('No hotel data available')
        
        competitors = Competitor.objects.filter(is_active=True)
        
        if hotel and competitors.exists():
            # Calculate daily metrics for the selected date range
            daily_data = calculate_daily_metrics_for_export(hotel, competitors, start_date, end_date)
            
            # Calculate month-to-date metrics
            mtd_start = today.replace(day=1)
            mtd_data = calculate_daily_metrics_for_export(hotel, competitors, mtd_start, today)
            
            # Calculate year-to-date metrics
            ytd_start = today.replace(month=1, day=1)
            ytd_data = calculate_daily_metrics_for_export(hotel, competitors, ytd_start, today)
            
            # Calculate totals for each period
            daily_totals = calculate_totals(daily_data)
            mtd_totals = calculate_totals(mtd_data)
            ytd_totals = calculate_totals(ytd_data)
            
    except Exception as e:
        return HttpResponseForbidden(f'Error processing data: {str(e)}')
    
    context = {
        'daily_data': daily_data,
        'mtd_data': mtd_data,
        'ytd_data': ytd_data,
        'daily_totals': daily_totals,
        'mtd_totals': mtd_totals,
        'ytd_totals': ytd_totals,
        'hotel': hotel,
        'start_date': start_date,
        'end_date': end_date
    }
    
    if format_type == 'excel':
        # Create Excel workbook
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        
        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#366092',
            'font_color': 'white',
            'border': 1
        })
        
        cell_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        percent_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'num_format': '0.00%'
        })
        
        currency_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'num_format': 'EGP#,##0.00'
        })
        
        # Create worksheets for each period
        periods = [
            ('Custom Date Range Performance', context.get('daily_data', {}), context.get('daily_totals', {}))
        ]
        
        for sheet_name, data, totals in periods:
            if data:
                worksheet = workbook.add_worksheet(sheet_name)
                
                # Set column widths
                worksheet.set_column('A:A', 20)  # Hotel name
                worksheet.set_column('B:O', 15)  # Metrics
                
                # Write headers
                headers = [
                    'Hotel', 'Total Rooms', 'Occupancy %', 'Average Rate', 'Sold Rooms',
                    'Room Revenue', 'RevPAR', 'Fair Market Share', 'Actual Market Share',
                    'MPI Rank', 'MPI', 'ARI Rank', 'ARI', 'RGI Rank', 'RGI'
                ]
                
                for col, header in enumerate(headers):
                    worksheet.write(0, col, header, header_format)
                
                # Write data
                row = 1
                for hotel_name, metrics in data.items():
                    worksheet.write(row, 0, hotel_name, cell_format)
                    worksheet.write(row, 1, metrics['rooms_available'], cell_format)
                    worksheet.write(row, 2, metrics['occupancy_percentage'] / 100, percent_format)
                    worksheet.write(row, 3, metrics['average_rate'], currency_format)
                    worksheet.write(row, 4, metrics['rooms_sold'], cell_format)
                    worksheet.write(row, 5, metrics['room_revenue'], currency_format)
                    worksheet.write(row, 6, metrics['revpar'], currency_format)
                    worksheet.write(row, 7, metrics['fair_market_share'] / 100, percent_format)
                    worksheet.write(row, 8, metrics['actual_market_share'] / 100, percent_format)
                    worksheet.write(row, 9, metrics['mpi_rank'], cell_format)
                    worksheet.write(row, 10, metrics['mpi'] / 100, percent_format)
                    worksheet.write(row, 11, metrics['ari_rank'], cell_format)
                    worksheet.write(row, 12, metrics['ari'] / 100, percent_format)
                    worksheet.write(row, 13, metrics['rgi_rank'], cell_format)
                    worksheet.write(row, 14, metrics['rgi'] / 100, percent_format)
                    row += 1
                
                # Write totals
                if totals:
                    worksheet.write(row, 0, 'Total', cell_format)
                    worksheet.write(row, 1, totals['rooms_available'], cell_format)
                    worksheet.write(row, 2, totals['occupancy_percentage'] / 100, percent_format)
                    worksheet.write(row, 3, totals['average_rate'], currency_format)
                    worksheet.write(row, 4, totals['rooms_sold'], cell_format)
                    worksheet.write(row, 5, totals['room_revenue'], currency_format)
                    worksheet.write(row, 6, totals['revpar'], currency_format)
                    worksheet.write(row, 7, 1, percent_format)  # 100%
                    worksheet.write(row, 8, 1, percent_format)  # 100%
                    worksheet.write_string(row, 9, '-', cell_format)
                    worksheet.write_string(row, 10, '-', cell_format)
                    worksheet.write_string(row, 11, '-', cell_format)
                    worksheet.write_string(row, 12, '-', cell_format)
                    worksheet.write_string(row, 13, '-', cell_format)
                    worksheet.write_string(row, 14, '-', cell_format)
        
        workbook.close()
        output.seek(0)
        
        # Create the HttpResponse object with Excel mime type
        response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=competitor_analytics_{date_range}.xlsx'
        return response
    
    else:  # PDF format
        # Create the HttpResponse object with PDF mime type
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=competitor_analytics_{date_range}.pdf'
        
        # Create the PDF object using ReportLab
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        
        doc = SimpleDocTemplate(response, pagesize=landscape(letter))
        elements = []
        styles = getSampleStyleSheet()
        
        # Title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30
        )
        
        # Add title
        elements.append(Paragraph('Competitor Analytics Report', title_style))
        elements.append(Spacer(1, 12))
        
        # Table headers
        headers = [
            'Hotel', 'Rooms\nAvailable', 'Occupancy\n%', 'Average\nRate', 'Sold\nRooms',
            'Room\nRevenue', 'RevPAR', 'Fair Market\nShare', 'Actual Market\nShare',
            'MPI\nRank', 'MPI', 'ARI\nRank', 'ARI', 'RGI\nRank', 'RGI'
        ]
        
        # Create tables for each period
        periods = [
            ('Custom Date Range Performance Metrics', context.get('daily_data', {}), context.get('daily_totals', {}))
        ]
        
        for title, data, totals in periods:
            if data:
                elements.append(Paragraph(title, title_style))
                elements.append(Spacer(1, 12))
                
                # Prepare table data
                table_data = [headers]
                
                for hotel_name, metrics in data.items():
                    row = [
                        hotel_name,
                        str(metrics['rooms_available']),
                        f"{metrics['occupancy_percentage']:.2f}%",
                        f"EGP{metrics['average_rate']:.2f}",
                        str(metrics['rooms_sold']),
                        f"EGP{metrics['room_revenue']:.2f}",
                        f"EGP{metrics['revpar']:.2f}",
                        f"{metrics['fair_market_share']:.2f}%",
                        f"{metrics['actual_market_share']:.2f}%",
                        str(metrics['mpi_rank']),
                        f"{metrics['mpi']:.2f}",
                        str(metrics['ari_rank']),
                        f"{metrics['ari']:.2f}",
                        str(metrics['rgi_rank']),
                        f"{metrics['rgi']:.2f}"
                    ]
                    table_data.append(row)
                
                # Add totals row
                if totals:
                    total_row = [
                        'Total',
                        str(totals['rooms_available']),
                        f"{totals['occupancy_percentage']:.2f}%",
                        f"EGP{totals['average_rate']:.2f}",
                        str(totals['rooms_sold']),
                        f"EGP{totals['room_revenue']:.2f}",
                        f"EGP{totals['revpar']:.2f}",
                        '100.00%',
                        '100.00%',
                        '-', '-', '-', '-', '-', '-'
                    ]
                    table_data.append(total_row)
                
                # Create table and set style
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.grey),
                    ('TEXTCOLOR', (0, -1), (-1, -1), colors.black),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, -1), (-1, -1), 10),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                elements.append(table)
                elements.append(Spacer(1, 20))
        
        # Build the PDF document
        doc.build(elements)
        return response


def calculate_daily_metrics_for_export(hotel, competitors, start_date, end_date):
    """Calculate daily metrics for export functionality"""
    data = {}
    
    # Calculate hotel metrics
    hotel_daily_data = DailyData.objects.filter(
        hotel=hotel,
        date__gte=start_date,
        date__lte=end_date
    )
    
    hotel_rooms_sold = hotel_daily_data.aggregate(Sum('rooms_sold'))['rooms_sold__sum'] or 0
    hotel_room_revenue = hotel_daily_data.aggregate(Sum('total_revenue'))['total_revenue__sum'] or 0
    hotel_occupancy = hotel_daily_data.aggregate(Avg('occupancy_percentage'))['occupancy_percentage__avg'] or 0
    hotel_avg_rate = hotel_daily_data.aggregate(Avg('average_rate'))['average_rate__avg'] or 0
    hotel_revpar = hotel_daily_data.aggregate(Avg('revpar'))['revpar__avg'] or 0
    
    # Get hotel performance indices
    hotel_performance = PerformanceIndex.objects.filter(
        hotel=hotel,
        competitor=None,
        date__gte=start_date,
        date__lte=end_date
    )
    
    hotel_mpi = hotel_performance.aggregate(Avg('mpi'))['mpi__avg'] or 0
    hotel_ari = hotel_performance.aggregate(Avg('ari'))['ari__avg'] or 0
    hotel_rgi = hotel_performance.aggregate(Avg('rgi'))['rgi__avg'] or 0
    hotel_fair_share = hotel_performance.aggregate(Avg('fair_market_share'))['fair_market_share__avg'] or 0
    hotel_actual_share = hotel_performance.aggregate(Avg('actual_market_share'))['actual_market_share__avg'] or 0
    
    data[hotel.name] = {
        'rooms_available': hotel.total_rooms,
        'rooms_sold': hotel_rooms_sold,
        'room_revenue': float(hotel_room_revenue),
        'occupancy_percentage': float(hotel_occupancy),
        'average_rate': float(hotel_avg_rate),
        'revpar': float(hotel_revpar),
        'fair_market_share': float(hotel_fair_share),
        'actual_market_share': float(hotel_actual_share),
        'mpi': float(hotel_mpi),
        'ari': float(hotel_ari),
        'rgi': float(hotel_rgi),
        'mpi_rank': 1,
        'ari_rank': 1,
        'rgi_rank': 1
    }
    
    # Calculate competitor metrics
    for competitor in competitors:
        comp_data = CompetitorData.objects.filter(
            competitor=competitor,
            date__gte=start_date,
            date__lte=end_date
        )
        
        comp_rooms_sold = comp_data.aggregate(Sum('rooms_sold'))['rooms_sold__sum'] or 0
        comp_occupancy = comp_data.aggregate(Avg('estimated_occupancy'))['estimated_occupancy__avg'] or 0
        comp_avg_rate = comp_data.aggregate(Avg('estimated_average_rate'))['estimated_average_rate__avg'] or 0
        
        comp_room_revenue = comp_rooms_sold * comp_avg_rate
        comp_revpar = comp_room_revenue / competitor.total_rooms if competitor.total_rooms > 0 else 0
        
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
        comp_fair_share = comp_performance.aggregate(Avg('fair_market_share'))['fair_market_share__avg'] or 0
        comp_actual_share = comp_performance.aggregate(Avg('actual_market_share'))['actual_market_share__avg'] or 0
        
        data[competitor.name] = {
            'rooms_available': competitor.total_rooms,
            'rooms_sold': comp_rooms_sold,
            'room_revenue': float(comp_room_revenue),
            'occupancy_percentage': float(comp_occupancy),
            'average_rate': float(comp_avg_rate),
            'revpar': float(comp_revpar),
            'fair_market_share': float(comp_fair_share),
            'actual_market_share': float(comp_actual_share),
            'mpi': float(comp_mpi),
            'ari': float(comp_ari),
            'rgi': float(comp_rgi),
            'mpi_rank': 1,
            'ari_rank': 1,
            'rgi_rank': 1
        }
    
    return data


def calculate_totals(data):
    """Calculate totals for a data dictionary"""
    if not data:
        return {}
    
    total_rooms_available = sum(item['rooms_available'] for item in data.values())
    total_rooms_sold = sum(item['rooms_sold'] for item in data.values())
    total_room_revenue = sum(item['room_revenue'] for item in data.values())
    
    avg_occupancy = (total_rooms_sold / total_rooms_available * 100) if total_rooms_available > 0 else 0
    avg_rate = (total_room_revenue / total_rooms_sold) if total_rooms_sold > 0 else 0
    revpar = (total_room_revenue / total_rooms_available) if total_rooms_available > 0 else 0
    
    return {
        'rooms_available': total_rooms_available,
        'rooms_sold': total_rooms_sold,
        'room_revenue': total_room_revenue,
        'occupancy_percentage': avg_occupancy,
        'average_rate': avg_rate,
        'revpar': revpar
    }
