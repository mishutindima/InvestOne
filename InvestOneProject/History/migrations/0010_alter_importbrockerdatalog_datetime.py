# Generated by Django 4.0.3 on 2022-11-03 18:55

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('History', '0009_historicalsharedeal_commission_currency_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='importbrockerdatalog',
            name='datetime',
            field=models.DateTimeField(default=datetime.datetime(2022, 11, 3, 21, 55, 8, 317708)),
        ),
    ]