from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hotel_management', '0005_competitor_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='competitordata',
            name='actual_market_share',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name='competitordata',
            name='ari',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='ARI'),
        ),
        migrations.AddField(
            model_name='competitordata',
            name='ari_rank',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='competitordata',
            name='fair_market_share',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name='competitordata',
            name='mpi',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='MPI'),
        ),
        migrations.AddField(
            model_name='competitordata',
            name='mpi_rank',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='competitordata',
            name='revpar',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='RevPAR'),
        ),
        migrations.AddField(
            model_name='competitordata',
            name='rgi',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='RGI'),
        ),
        migrations.AddField(
            model_name='competitordata',
            name='rgi_rank',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]