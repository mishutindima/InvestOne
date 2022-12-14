# Generated by Django 4.0.3 on 2022-11-03 18:50

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('History', '0008_alter_importbrockerdatalog_datetime'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalsharedeal',
            name='commission_currency',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True,
                                    on_delete=django.db.models.deletion.DO_NOTHING, related_name='+',
                                    to='History.currency'),
        ),
        migrations.AddField(
            model_name='sharedeal',
            name='commission_currency',
            field=models.ForeignKey(default='RUB', on_delete=django.db.models.deletion.PROTECT, related_name='+',
                                    to='History.currency'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='importbrockerdatalog',
            name='datetime',
            field=models.DateTimeField(default=datetime.datetime(2022, 11, 3, 21, 50, 0, 688578)),
        ),
    ]
