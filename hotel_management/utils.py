from django.db import models
from decimal import Decimal
from datetime import datetime
from .models import CompetitorData

def update_market_summary(date, skip_performance_update=False):
    """
    Update or create market summary and performance indices for a specific date
    This function is called after saving DailyData or CompetitorData
    
    Args:
        date: The date to update market summary for
        skip_performance_update: If True, skip updating performance indices to prevent recursion
    """
    # Import here to avoid circular imports
    from .models import Hotel, Competitor, DailyData, CompetitorData, MarketSummary, PerformanceIndex
    
    # Convert string date to date object if needed
    if isinstance(date, str):
        try:
            date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            print(f"Error: Invalid date format {date}")
            return
    
    # Get the hotel and active competitors
    hotel = Hotel.objects.first()
    competitors = Competitor.objects.filter(is_active=True)
    
    if not hotel:
        return  # No hotel data, can't calculate
    
    # Get hotel data for the date
    hotel_data = DailyData.objects.filter(hotel=hotel, date=date).first()
    if not hotel_data:
        return  # No hotel data for this date
    
    # Get competitor data for the date
    competitor_data_list = CompetitorData.objects.filter(competitor__in=competitors, date=date)
    
    # Calculate totals for market summary
    total_rooms_available = hotel.total_rooms
    total_rooms_sold = hotel_data.rooms_sold
    total_revenue = hotel_data.total_revenue
    
    for comp_data in competitor_data_list:
        total_rooms_available += comp_data.competitor.total_rooms
        total_rooms_sold += comp_data.rooms_sold
        # Calculate competitor revenue
        comp_revenue = Decimal(comp_data.rooms_sold) * Decimal(comp_data.estimated_average_rate)
        total_revenue += comp_revenue
    
    # Create or update market summary
    market_summary, created = MarketSummary.objects.update_or_create(
        date=date,
        defaults={
            'total_rooms_available': total_rooms_available,
            'total_rooms_sold': total_rooms_sold,
            'total_revenue': total_revenue,
        }
    )
    
    if not skip_performance_update:
        # Calculate and update hotel performance indices
        update_hotel_performance_indices(hotel, hotel_data, market_summary)
        
        # Calculate and update competitor performance indices
        for comp_data in competitor_data_list:
            update_competitor_performance_indices(comp_data.competitor, comp_data, market_summary)
        
        # Update performance rankings
        update_performance_rankings(date)

def update_hotel_performance_indices(hotel, hotel_data, market_summary):
    """
    Update performance indices for the hotel
    """
    from .models import PerformanceIndex
    
    # Calculate fair and actual market share
    fair_market_share = Decimal('0.00')
    actual_market_share = Decimal('0.00')
    mpi = Decimal('0.00')
    ari = Decimal('0.00')
    rgi = Decimal('0.00')
    
    if market_summary.total_rooms_available > 0:
        fair_market_share = (Decimal(hotel.total_rooms) / Decimal(market_summary.total_rooms_available)) * Decimal('100')
    
    if market_summary.total_rooms_sold > 0:
        actual_market_share = (Decimal(hotel_data.rooms_sold) / Decimal(market_summary.total_rooms_sold)) * Decimal('100')
    
    # Calculate MPI (Market Penetration Index)
    if fair_market_share > 0:
        mpi = actual_market_share / fair_market_share * Decimal('100')
    
    # Calculate ARI (Average Rate Index)
    if market_summary.market_adr > 0:
        ari = hotel_data.average_rate / market_summary.market_adr * Decimal('100')
    
    # Calculate RGI (Revenue Generation Index)
    if market_summary.market_revpar > 0:
        rgi = hotel_data.revpar / market_summary.market_revpar * Decimal('100')
    
    # Create or update performance index for hotel
    PerformanceIndex.objects.update_or_create(
        date=hotel_data.date,
        hotel=hotel,
        competitor=None,  # No competitor for hotel's own index
        market_summary=market_summary,
        defaults={
            'fair_market_share': fair_market_share,
            'actual_market_share': actual_market_share,
            'mpi': mpi,
            'ari': ari,
            'rgi': rgi,
        }
    )

def update_competitor_performance_indices(competitor, comp_data, market_summary):
    """
    Update performance indices for a competitor
    """
    from .models import Hotel, PerformanceIndex
    from django.db import transaction
    
    hotel = Hotel.objects.first()
    if not hotel:
        return
    
    # Calculate fair and actual market share
    fair_market_share = Decimal('0.00')
    actual_market_share = Decimal('0.00')
    mpi = Decimal('0.00')
    ari = Decimal('0.00')
    rgi = Decimal('0.00')
    
    if market_summary.total_rooms_available > 0:
        fair_market_share = (Decimal(competitor.total_rooms) / Decimal(market_summary.total_rooms_available)) * Decimal('100')
    
    if market_summary.total_rooms_sold > 0:
        actual_market_share = (Decimal(comp_data.rooms_sold) / Decimal(market_summary.total_rooms_sold)) * Decimal('100')
    
    # Calculate MPI (Market Penetration Index)
    if fair_market_share > 0:
        mpi = actual_market_share / fair_market_share * Decimal('100')
    
    # Calculate ARI (Average Rate Index)
    if market_summary.market_adr > 0:
        ari = Decimal(comp_data.estimated_average_rate) / market_summary.market_adr * Decimal('100')
    
    # Calculate RGI (Revenue Generation Index)
    if market_summary.market_revpar > 0:
        rgi = comp_data.revpar / market_summary.market_revpar * Decimal('100')
    
    with transaction.atomic():
        # Update competitor data with performance indices
        CompetitorData.objects.filter(id=comp_data.id).update(
            occupancy_index=mpi,
            adr_index=ari,
            revenue_index=rgi
        )
        
        # Create or update performance index for competitor
        PerformanceIndex.objects.update_or_create(
            date=comp_data.date,
            hotel=hotel,
            competitor=competitor,
            market_summary=market_summary,
            defaults={
                'fair_market_share': fair_market_share,
                'actual_market_share': actual_market_share,
                'mpi': mpi,
                'ari': ari,
                'rgi': rgi,
            }
        )

def update_performance_rankings(date):
    """
    Update performance rankings for all competitors on a specific date
    """
    from .models import Hotel, PerformanceIndex
    
    # Convert string date to date object if needed
    if isinstance(date, str):
        try:
            date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            print(f"Error: Invalid date format {date}")
            return
    
    hotel = Hotel.objects.first()
    if not hotel:
        return
    
    # Get all performance indices for the date
    indices = PerformanceIndex.objects.filter(date=date).exclude(competitor=None)
    
    # Sort by MPI, ARI, RGI, handling null values
    # First, sort by the metric value, then by competitor name for consistent ordering
    mpi_sorted = sorted(
        [i for i in indices if i.mpi is not None],
        key=lambda x: (x.mpi, x.competitor.name if x.competitor else ''),
        reverse=True
    )
    ari_sorted = sorted(
        [i for i in indices if i.ari is not None],
        key=lambda x: (x.ari, x.competitor.name if x.competitor else ''),
        reverse=True
    )
    rgi_sorted = sorted(
        [i for i in indices if i.rgi is not None],
        key=lambda x: (x.rgi, x.competitor.name if x.competitor else ''),
        reverse=True
    )
    
    # Add indices with null values at the end
    mpi_null = sorted([i for i in indices if i.mpi is None], key=lambda x: x.competitor.name if x.competitor else '')
    ari_null = sorted([i for i in indices if i.ari is None], key=lambda x: x.competitor.name if x.competitor else '')
    rgi_null = sorted([i for i in indices if i.rgi is None], key=lambda x: x.competitor.name if x.competitor else '')
    
    mpi_sorted.extend(mpi_null)
    ari_sorted.extend(ari_null)
    rgi_sorted.extend(rgi_null)
    
    # Update rankings
    rank_updates = {}
    
    # Helper function to update ranks
    def update_rank(sorted_indices, rank_field):
        current_rank = 1
        prev_value = None
        for index in sorted_indices:
            current_value = getattr(index, rank_field.replace('_rank', ''))
            # Same value gets same rank
            if prev_value is not None and current_value == prev_value:
                rank = rank_updates[sorted_indices[current_rank-2].id]['ranks'][rank_field]
            else:
                rank = current_rank
            
            if index.id not in rank_updates:
                rank_updates[index.id] = {'index': index, 'ranks': {}}
            rank_updates[index.id]['ranks'][rank_field] = rank
            
            prev_value = current_value
            current_rank += 1
    
    # Update ranks for each metric
    update_rank(mpi_sorted, 'mpi_rank')
    update_rank(ari_sorted, 'ari_rank')
    update_rank(rgi_sorted, 'rgi_rank')
    
    # Bulk update all rankings in a single save per index
    for update_data in rank_updates.values():
        index = update_data['index']
        ranks = update_data['ranks']
        update_fields = []
        for field, value in ranks.items():
            setattr(index, field, value)
            update_fields.append(field)
        if update_fields:  # Only save if there are fields to update
            index.save(update_fields=update_fields)