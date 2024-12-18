# Generated by Django 5.1.4 on 2024-12-17 10:59

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CarbonFootprintEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transport_mode', models.CharField(choices=[('bus', 'Bus'), ('train', 'Train'), ('metro', 'Metro'), ('auto', 'Auto-Rickshaw')], max_length=10)),
                ('distance', models.FloatField()),
                ('travel_date', models.DateField(auto_now_add=True)),
                ('daily_emissions', models.FloatField(default=0)),
                ('annual_emissions_equivalent', models.FloatField(default=0)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UserRewardProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_points', models.IntegerField(default=0)),
                ('total_emissions_saved', models.FloatField(default=0)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
