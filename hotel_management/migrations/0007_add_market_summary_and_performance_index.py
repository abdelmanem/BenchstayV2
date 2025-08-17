from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('hotel_management', '0006_add_calculated_metrics_to_competitordata'),
    ]

    operations = [
        migrations.CreateModel(
            name='MarketSummary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(unique=True)),
                ('total_rooms_available', models.IntegerField()),
                ('total_rooms_sold', models.IntegerField()),
                ('total_revenue', models.DecimalField(decimal_places=2, max_digits=12)),
                ('market_occupancy', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('market_adr', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='Market ADR')),
                ('market_revpar', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='Market RevPAR')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name_plural': 'Market Summaries',
                'ordering': ['-date'],
            },
        ),
        migrations.CreateModel(
            name='PerformanceIndex',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('fair_market_share', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('actual_market_share', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('mpi', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='MPI')),
                ('ari', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='ARI')),
                ('rgi', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='RGI')),
                ('mpi_rank', models.IntegerField(blank=True, null=True)),
                ('ari_rank', models.IntegerField(blank=True, null=True)),
                ('rgi_rank', models.IntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('competitor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='performance_indices', to='hotel_management.competitor')),
                ('hotel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='performance_indices', to='hotel_management.hotel')),
                ('market_summary', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='performance_indices', to='hotel_management.marketsummary')),
            ],
            options={
                'ordering': ['-date'],
                'unique_together': {('date', 'hotel', 'competitor')},
            },
        ),
    ]