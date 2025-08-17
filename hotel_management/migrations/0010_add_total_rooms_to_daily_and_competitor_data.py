from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hotel_management', '0009_populate_market_summary_and_performance_index'),
    ]

    operations = [
        migrations.AddField(
            model_name='dailydata',
            name='total_rooms',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='competitordata',
            name='total_rooms',
            field=models.IntegerField(default=0),
        ),
    ]