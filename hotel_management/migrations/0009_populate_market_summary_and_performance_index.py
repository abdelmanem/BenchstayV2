from django.db import migrations
from decimal import Decimal

def migrate_data(apps, schema_editor):
    # Get the models
    Hotel = apps.get_model('hotel_management', 'Hotel')
    Competitor = apps.get_model('hotel_management', 'Competitor')
    DailyData = apps.get_model('hotel_management', 'DailyData')
    CompetitorData = apps.get_model('hotel_management', 'CompetitorData')
    MarketSummary = apps.get_model('hotel_management', 'MarketSummary')
    PerformanceIndex = apps.get_model('hotel_management', 'PerformanceIndex')
    
    # Get the hotel
    hotel = Hotel.objects.first()
    if not hotel:
        return
    
    # Get all dates with competitor data
    dates = CompetitorData.objects.values_list('date', flat=True).distinct()
    
    for date in dates:
        # Get hotel data for the date
        hotel_data = DailyData.objects.filter(hotel=hotel, date=date).first()
        if not hotel_data:
            continue
        
        # Get competitor data for the date
        competitor_data_list = CompetitorData.objects.filter(date=date)
        if not competitor_data_list.exists():
            continue
        
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
                'total_revenue': total_revenue
            }
        )
        
        # Calculate market metrics
        if total_rooms_available > 0:
            market_summary.market_occupancy = (Decimal(total_rooms_sold) / Decimal(total_rooms_available)) * Decimal('100')
        else:
            market_summary.market_occupancy = Decimal('0.00')
            
        if total_rooms_sold > 0:
            market_summary.market_adr = total_revenue / Decimal(total_rooms_sold)
        else:
            market_summary.market_adr = Decimal('0.00')
            
        if total_rooms_available > 0:
            market_summary.market_revpar = total_revenue / Decimal(total_rooms_available)
        else:
            market_summary.market_revpar = Decimal('0.00')
            
        market_summary.save()
        
        # Create hotel performance index
        fair_market_share = Decimal('0.00')
        actual_market_share = Decimal('0.00')
        mpi = Decimal('0.00')
        ari = Decimal('0.00')
        rgi = Decimal('0.00')
        
        if total_rooms_available > 0:
            fair_market_share = (Decimal(hotel.total_rooms) / Decimal(total_rooms_available)) * Decimal('100')
        
        if total_rooms_sold > 0:
            actual_market_share = (Decimal(hotel_data.rooms_sold) / Decimal(total_rooms_sold)) * Decimal('100')
        
        if fair_market_share > 0:
            mpi = actual_market_share / fair_market_share * Decimal('100')
        
        if market_summary.market_adr > 0:
            ari = hotel_data.average_rate / market_summary.market_adr * Decimal('100')
        
        if market_summary.market_revpar > 0:
            rgi = hotel_data.revpar / market_summary.market_revpar * Decimal('100')
        
        PerformanceIndex.objects.update_or_create(
            date=date,
            hotel=hotel,
            competitor=None,
            defaults={
                'market_summary': market_summary,
                'fair_market_share': fair_market_share,
                'actual_market_share': actual_market_share,
                'mpi': mpi,
                'ari': ari,
                'rgi': rgi
            }
        )
        
        # Create competitor performance indices
        for comp_data in competitor_data_list:
            fair_market_share = Decimal('0.00')
            actual_market_share = Decimal('0.00')
            mpi = Decimal('0.00')
            ari = Decimal('0.00')
            rgi = Decimal('0.00')
            
            if total_rooms_available > 0:
                fair_market_share = (Decimal(comp_data.competitor.total_rooms) / Decimal(total_rooms_available)) * Decimal('100')
            
            if total_rooms_sold > 0:
                actual_market_share = (Decimal(comp_data.rooms_sold) / Decimal(total_rooms_sold)) * Decimal('100')
            
            if fair_market_share > 0:
                mpi = actual_market_share / fair_market_share * Decimal('100')
            
            if market_summary.market_adr > 0:
                ari = Decimal(comp_data.estimated_average_rate) / market_summary.market_adr * Decimal('100')
            
            if market_summary.market_revpar > 0 and comp_data.revpar is not None:
                rgi = comp_data.revpar / market_summary.market_revpar * Decimal('100')
            else:
                rgi = Decimal('0.00')
            
            # Use existing rank values from CompetitorData if available
            PerformanceIndex.objects.update_or_create(
                date=date,
                hotel=hotel,
                competitor=comp_data.competitor,
                defaults={
                    'market_summary': market_summary,
                    'fair_market_share': fair_market_share,
                    'actual_market_share': actual_market_share,
                    'mpi': mpi,
                    'ari': ari,
                    'rgi': rgi,
                    'mpi_rank': getattr(comp_data, 'mpi_rank', None),
                    'ari_rank': getattr(comp_data, 'ari_rank', None),
                    'rgi_rank': getattr(comp_data, 'rgi_rank', None)
                }
            )


class Migration(migrations.Migration):

    dependencies = [
        ('hotel_management', '0008_remove_redundant_fields_from_competitordata'),
    ]

    operations = [
        migrations.RunPython(migrate_data, migrations.RunPython.noop),
    ]