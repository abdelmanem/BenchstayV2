from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('hotel_management', '0013_hotel_logo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dailydata',
            name='total_revenue',
            field=models.DecimalField(decimal_places=2, max_digits=12),
        ),
    ]