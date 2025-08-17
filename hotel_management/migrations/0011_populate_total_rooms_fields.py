from django.db import migrations

def populate_total_rooms(apps, schema_editor):
    # Get the models
    Hotel = apps.get_model('hotel_management', 'Hotel')
    Competitor = apps.get_model('hotel_management', 'Competitor')
    DailyData = apps.get_model('hotel_management', 'DailyData')
    CompetitorData = apps.get_model('hotel_management', 'CompetitorData')
    
    # Get all hotel data entries and update with hotel's total_rooms
    hotel_data_entries = DailyData.objects.all()
    for entry in hotel_data_entries:
        entry.total_rooms = entry.hotel.total_rooms
        entry.save()
    
    # Get all competitor data entries and update with competitor's total_rooms
    competitor_data_entries = CompetitorData.objects.all()
    for entry in competitor_data_entries:
        entry.total_rooms = entry.competitor.total_rooms
        entry.save()


class Migration(migrations.Migration):

    dependencies = [
        ('hotel_management', '0010_add_total_rooms_to_daily_and_competitor_data'),
    ]

    operations = [
        migrations.RunPython(populate_total_rooms),
    ]