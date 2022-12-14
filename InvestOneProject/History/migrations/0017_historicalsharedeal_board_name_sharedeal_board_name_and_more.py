# Generated by Django 4.1 on 2022-12-02 19:02

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "History",
            "0016_rename_count_historicalsharedeal_count_without_sign_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalsharedeal",
            name="board_name",
            field=models.CharField(
                choices=[
                    ("MOSCOW_BOARD", "Московская биржа"),
                    ("SPB_BOARD", "Санкт-Петербургская биржа (ФР СПб)"),
                ],
                default="MOSCOW_BOARD",
                max_length=20,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="sharedeal",
            name="board_name",
            field=models.CharField(
                choices=[
                    ("MOSCOW_BOARD", "Московская биржа"),
                    ("SPB_BOARD", "Санкт-Петербургская биржа (ФР СПб)"),
                ],
                default="MOSCOW_BOARD",
                max_length=20,
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="importbrockerdatalog",
            name="datetime",
            field=models.DateTimeField(
                default=datetime.datetime(2022, 12, 2, 22, 1, 33, 13601)
            ),
        ),
    ]
