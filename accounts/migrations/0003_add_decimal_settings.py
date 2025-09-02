from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_systemsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemsettings',
            name='decimal_places_percentage',
            field=models.IntegerField(default=1, help_text='Decimal places for percentages (e.g., occupancy, indices)'),
        ),
        migrations.AddField(
            model_name='systemsettings',
            name='decimal_places_currency',
            field=models.IntegerField(default=2, help_text='Decimal places for currency values (e.g., ADR, RevPAR)'),
        ),
    ]


