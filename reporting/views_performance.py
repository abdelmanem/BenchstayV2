import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Avg, Sum, F, Q
from datetime import timedelta, datetime
from decimal import Decimal
from hotel_management.models import Hotel, Competitor, DailyData, CompetitorData, MarketSummary, PerformanceIndex

@login_required
def hotel_performance_report(request, hotel_id=None):
    """
    Generate a comprehensive hotel performance report with interactive visualizations
    using Plotly and Bootstrap.
    """
    # Get hotel (either specified or default)
    if hotel_id:
        hotel = get_object_or_404(Hotel, id=hotel_id)
    else:
        hotel = Hotel.objects.first()
    
    # If no hotel exists yet, redirect to hotel data page
    if not hotel:
        messages.info(request, 'Please set up your hotel information first')
        return redirect('hotel_management:hotel_data')
    
    # Default to last 30 days
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Handle date range selection
    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    # Get hotel data for the selected period
    hotel_data = DailyData.objects.filter(
        hotel=hotel,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date')
    
    # Get market summaries for the selected period
    market_summaries = MarketSummary.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date')
    
    # Get performance indices for the selected period
    performance_indices = PerformanceIndex.objects.filter(
        hotel=hotel,
        date__gte=start_date,
        date__lte=end_date,
        competitor__isnull=True  # Only get hotel's own indices
    ).order_by('date')
    
    # Calculate summary statistics
    summary = {
        'current_occ': hotel_data.last().occupancy_percentage if hotel_data.exists() else Decimal('0.00'),
        'avg_occupancy': hotel_data.aggregate(Avg('occupancy_percentage'))['occupancy_percentage__avg'] or Decimal('0.00'),
        'avg_rate': hotel_data.aggregate(Avg('average_rate'))['average_rate__avg'] or Decimal('0.00'),
        'avg_revpar': hotel_data.aggregate(Avg('revpar'))['revpar__avg'] or Decimal('0.00'),
        'total_revenue': hotel_data.aggregate(Sum('total_revenue'))['total_revenue__sum'] or Decimal('0.00'),
    }
    
    # Calculate Year-over-Year changes if data available
    last_year_start = start_date.replace(year=start_date.year-1)
    last_year_end = end_date.replace(year=end_date.year-1)
    
    last_year_data = DailyData.objects.filter(
        hotel=hotel,
        date__gte=last_year_start,
        date__lte=last_year_end
    )
    
    def percent_change(current, previous):
        if previous and previous != 0:
            return ((current - previous) / previous) * 100
        return Decimal('0.00')
    
    if last_year_data.exists():
        last_year_avg_occ = last_year_data.aggregate(Avg('occupancy_percentage'))['occupancy_percentage__avg'] or Decimal('0.00')
        last_year_avg_rate = last_year_data.aggregate(Avg('average_rate'))['average_rate__avg'] or Decimal('0.00')
        last_year_avg_revpar = last_year_data.aggregate(Avg('revpar'))['revpar__avg'] or Decimal('0.00')
        last_year_total_revenue = last_year_data.aggregate(Sum('total_revenue'))['total_revenue__sum'] or Decimal('0.00')
        
        summary['occ_change'] = percent_change(summary['avg_occupancy'], last_year_avg_occ)
        summary['rate_change'] = percent_change(summary['avg_rate'], last_year_avg_rate)
        summary['revpar_change'] = percent_change(summary['avg_revpar'], last_year_avg_revpar)
        summary['revenue_change'] = percent_change(summary['total_revenue'], last_year_total_revenue)
    else:
        summary['occ_change'] = Decimal('0.00')
        summary['rate_change'] = Decimal('0.00')
        summary['revpar_change'] = Decimal('0.00')
        summary['revenue_change'] = Decimal('0.00')
    
    # Convert to Pandas DataFrame for Plotly
    df_hotel = pd.DataFrame(list(hotel_data.values('date', 'occupancy_percentage', 'average_rate', 'revpar')))
    df_market = pd.DataFrame(list(market_summaries.values('date', 'market_occupancy', 'market_adr', 'market_revpar')))
    df_indices = pd.DataFrame(list(performance_indices.values('date', 'mpi', 'ari', 'rgi')))
    
    # Generate Performance Trend Chart
    if not df_hotel.empty:
        trend_fig = px.line(df_hotel, x="date", y=["occupancy_percentage", "average_rate", "revpar"],
                        title="Monthly Performance Trends",
                        labels={"value": "Performance Metrics", "date": "Date", 
                                "variable": "Metric"},
                        template="plotly_white")
        
        # Update line colors and names
        trend_fig.update_traces(
            line=dict(width=3),
            selector=dict(name="occupancy_percentage"),
            name="Occupancy %"
        )
        trend_fig.update_traces(
            line=dict(width=3),
            selector=dict(name="average_rate"),
            name="ADR"
        )
        trend_fig.update_traces(
            line=dict(width=3),
            selector=dict(name="revpar"),
            name="RevPAR"
        )
        
        trend_chart = trend_fig.to_html(full_html=False, include_plotlyjs='cdn')
    else:
        trend_chart = "<div class='alert alert-info'>No data available for the selected period</div>"
    
    # Generate Market Comparison Chart
    if not df_hotel.empty and not df_market.empty:
        # Merge hotel and market data
        df_comparison = pd.merge(df_hotel, df_market, on='date')
        
        # Create figure with secondary y-axis
        comp_fig = go.Figure()
        
        # Add traces for hotel and market occupancy
        comp_fig.add_trace(
            go.Bar(x=df_comparison['date'], y=df_comparison['occupancy_percentage'],
                   name="Hotel Occupancy", marker_color='rgba(0, 123, 255, 0.7)')
        )
        comp_fig.add_trace(
            go.Bar(x=df_comparison['date'], y=df_comparison['market_occupancy'],
                   name="Market Occupancy", marker_color='rgba(40, 167, 69, 0.7)')
        )
        
        # Set title and layout
        comp_fig.update_layout(
            title="Hotel vs Market Occupancy",
            template="plotly_white",
            barmode='group',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        comparison_chart = comp_fig.to_html(full_html=False, include_plotlyjs='cdn')
    else:
        comparison_chart = "<div class='alert alert-info'>No market data available for comparison</div>"
    
    # Generate Performance Indices Chart
    if not df_indices.empty:
        indices_fig = px.line(df_indices, x="date", y=["mpi", "ari", "rgi"],
                           title="Performance Indices Trends",
                           labels={"value": "Index Value", "date": "Date", 
                                   "variable": "Index Type"},
                           template="plotly_white")
        
        # Update line colors and names
        indices_fig.update_traces(
            line=dict(width=3, color='rgba(255, 99, 132, 1)'),
            selector=dict(name="mpi"),
            name="MPI"
        )
        indices_fig.update_traces(
            line=dict(width=3, color='rgba(54, 162, 235, 1)'),
            selector=dict(name="ari"),
            name="ARI"
        )
        indices_fig.update_traces(
            line=dict(width=3, color='rgba(255, 206, 86, 1)'),
            selector=dict(name="rgi"),
            name="RGI"
        )
        
        # Add a reference line at 100
        indices_fig.add_shape(
            type="line",
            x0=df_indices['date'].min(),
            y0=100,
            x1=df_indices['date'].max(),
            y1=100,
            line=dict(color="gray", width=1, dash="dash")
        )
        
        indices_chart = indices_fig.to_html(full_html=False, include_plotlyjs='cdn')
    else:
        indices_chart = "<div class='alert alert-info'>No performance indices available for the selected period</div>"
    
    # Generate RevPAR % Change Chart (YoY if available)
    if not df_hotel.empty and last_year_data.exists():
        # Calculate RevPAR % change for each date
        revpar_changes = []
        for data in hotel_data:
            # Find matching date from last year
            last_year_date = data.date.replace(year=data.date.year-1)
            last_year_entry = last_year_data.filter(date=last_year_date).first()
            
            if last_year_entry and last_year_entry.revpar > 0:
                change = ((data.revpar - last_year_entry.revpar) / last_year_entry.revpar) * 100
                revpar_changes.append({
                    'date': data.date,
                    'change': float(change)
                })
        
        if revpar_changes:
            df_revpar_change = pd.DataFrame(revpar_changes)
            revpar_fig = px.bar(df_revpar_change, x="date", y="change", 
                              title="RevPAR % Change (Year-over-Year)",
                              labels={"change": "% Change", "date": "Date"},
                              template="plotly_white")
            
            # Color bars based on positive/negative values
            revpar_fig.update_traces(
                marker_color=['rgba(40, 167, 69, 0.7)' if c >= 0 else 'rgba(220, 53, 69, 0.7)' 
                              for c in df_revpar_change['change']]
            )
            
            # Add a reference line at 0
            revpar_fig.add_shape(
                type="line",
                x0=df_revpar_change['date'].min(),
                y0=0,
                x1=df_revpar_change['date'].max(),
                y1=0,
                line=dict(color="black", width=1)
            )
            
            revpar_chart = revpar_fig.to_html(full_html=False, include_plotlyjs='cdn')
        else:
            revpar_chart = "<div class='alert alert-info'>No year-over-year data available for RevPAR comparison</div>"
    else:
        revpar_chart = "<div class='alert alert-info'>No year-over-year data available for RevPAR comparison</div>"
    
    context = {
        "title": "Hotel Performance Report - Benchstay",
        "hotel": hotel,
        "summary": summary,
        "start_date": start_date,
        "end_date": end_date,
        "trend_chart": trend_chart,
        "comparison_chart": comparison_chart,
        "indices_chart": indices_chart,
        "revpar_chart": revpar_chart,
    }
    
    return render(request, "reporting/hotel_performance.html", context)