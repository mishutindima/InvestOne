# Generated by Django 4.1 on 2022-11-06 16:10

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('History', '0010_alter_importbrockerdatalog_datetime'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalmoneydeal',
            name='comment',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='moneydeal',
            name='comment',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='historicalmoneydeal',
            name='commission',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AlterField(
            model_name='historicalmoneydeal',
            name='operation_number',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='historicalmoneydeal',
            name='tax',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AlterField(
            model_name='historicalmoneydeal',
            name='type_of_deal',
            field=models.CharField(
                choices=[('BUY_SR', 'Покупка акций'), ('SL_SR', 'Продажа акций'), ('DIV', 'Выплата дивидендов/купонов'),
                         ('BUY_BND', 'Покупка облигаций'), ('SL_BND', 'Продажа облигаций'),
                         ('RFL_MN', 'Внесение денег на счет'), ('WD_MN', 'Вывод денег со счета'),
                         ('BRK_CM', 'Брокерская комиссия'), ('TAX', 'Налоги'), ('UNKNOWN', 'Не распознанный тип'),
                         ('ERR', 'Ошибка')], max_length=10),
        ),
        migrations.AlterField(
            model_name='historicalsharedeal',
            name='type_of_deal',
            field=models.CharField(
                choices=[('BUY_SR', 'Покупка акций'), ('SL_SR', 'Продажа акций'), ('DIV', 'Выплата дивидендов/купонов'),
                         ('BUY_BND', 'Покупка облигаций'), ('SL_BND', 'Продажа облигаций'),
                         ('RFL_MN', 'Внесение денег на счет'), ('WD_MN', 'Вывод денег со счета'),
                         ('BRK_CM', 'Брокерская комиссия'), ('TAX', 'Налоги'), ('UNKNOWN', 'Не распознанный тип'),
                         ('ERR', 'Ошибка')], max_length=10),
        ),
        migrations.AlterField(
            model_name='importbrockerdatalog',
            name='datetime',
            field=models.DateTimeField(default=datetime.datetime(2022, 11, 6, 19, 10, 57, 834558)),
        ),
        migrations.AlterField(
            model_name='moneydeal',
            name='brocker_periodic_commissions',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                    to='History.brockerperiodiccommissions'),
        ),
        migrations.AlterField(
            model_name='moneydeal',
            name='commission',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AlterField(
            model_name='moneydeal',
            name='operation_number',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='moneydeal',
            name='share_by_divident',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                    to='History.share'),
        ),
        migrations.AlterField(
            model_name='moneydeal',
            name='tax',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AlterField(
            model_name='moneydeal',
            name='type_of_deal',
            field=models.CharField(
                choices=[('BUY_SR', 'Покупка акций'), ('SL_SR', 'Продажа акций'), ('DIV', 'Выплата дивидендов/купонов'),
                         ('BUY_BND', 'Покупка облигаций'), ('SL_BND', 'Продажа облигаций'),
                         ('RFL_MN', 'Внесение денег на счет'), ('WD_MN', 'Вывод денег со счета'),
                         ('BRK_CM', 'Брокерская комиссия'), ('TAX', 'Налоги'), ('UNKNOWN', 'Не распознанный тип'),
                         ('ERR', 'Ошибка')], max_length=10),
        ),
        migrations.AlterField(
            model_name='sharedeal',
            name='type_of_deal',
            field=models.CharField(
                choices=[('BUY_SR', 'Покупка акций'), ('SL_SR', 'Продажа акций'), ('DIV', 'Выплата дивидендов/купонов'),
                         ('BUY_BND', 'Покупка облигаций'), ('SL_BND', 'Продажа облигаций'),
                         ('RFL_MN', 'Внесение денег на счет'), ('WD_MN', 'Вывод денег со счета'),
                         ('BRK_CM', 'Брокерская комиссия'), ('TAX', 'Налоги'), ('UNKNOWN', 'Не распознанный тип'),
                         ('ERR', 'Ошибка')], max_length=10),
        ),
    ]
