from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hotel_management', '0007_add_market_summary_and_performance_index'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='competitordata',
            name='fair_market_share',
        ),
        migrations.RemoveField(
            model_name='competitordata',
            name='actual_market_share',
        ),
        migrations.RemoveField(
            model_name='competitordata',
            name='mpi',
        ),
        migrations.RemoveField(
            model_name='competitordata',
            name='ari',
        ),
        migrations.RemoveField(
            model_name='competitordata',
            name='rgi',
        ),
        migrations.RemoveField(
            model_name='competitordata',
            name='mpi_rank',
        ),
        migrations.RemoveField(
            model_name='competitordata',
            name='ari_rank',
        ),
        migrations.RemoveField(
            model_name='competitordata',
            name='rgi_rank',
        ),
    ]