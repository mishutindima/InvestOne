# Generated by Django 4.0.3 on 2022-09-25 12:35

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('History', '0004_importbrockerdatalog'),
    ]

    operations = [
        migrations.AlterField(
            model_name='importbrockerdatalog',
            name='datetime',
            field=models.DateTimeField(default=datetime.datetime(2022, 9, 25, 15, 35, 17, 124285)),
        ),
        migrations.AlterField(
            model_name='importbrockerdatalog',
            name='file_or_content',
            field=models.FileField(upload_to='import_brocker_data_log/'),
        ),
        migrations.AlterField(
            model_name='importbrockerdatalog',
            name='status_code',
            field=models.IntegerField(default=0),
        ),
    ]
