# Generated by Django 4.1 on 2022-11-29 07:13

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("History", "0015_rename_bill_alternativenameofshare_share_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="historicalsharedeal",
            old_name="count",
            new_name="count_without_sign",
        ),
        migrations.RenameField(
            model_name="historicalsharedeal",
            old_name="price",
            new_name="price_with_sign",
        ),
        migrations.RenameField(
            model_name="sharedeal",
            old_name="count",
            new_name="count_without_sign",
        ),
        migrations.RenameField(
            model_name="sharedeal",
            old_name="price",
            new_name="price_with_sign",
        ),
        migrations.AlterField(
            model_name="importbrockerdatalog",
            name="datetime",
            field=models.DateTimeField(
                default=datetime.datetime(2022, 11, 29, 10, 12, 59, 900802)
            ),
        ),
    ]
