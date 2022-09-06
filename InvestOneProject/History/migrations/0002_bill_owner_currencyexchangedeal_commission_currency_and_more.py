# Generated by Django 4.0.3 on 2022-09-06 20:05

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('History', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='bill',
            name='owner',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='currencyexchangedeal',
            name='commission_currency',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='History.currency'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='investrecommendation',
            name='owner',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='moneydeal',
            name='type_of_deal',
            field=models.CharField(choices=[('BUY_SR', 'Покупка акций'), ('SL_SR', 'Продажа акций'), ('DIV', 'Выплата дивидендов/купонов'), ('BUY_BND', 'Покупка облигаций'), ('SL_BND', 'Продажа облигаций'), ('RFL_MN', 'Внесение денег на счет'), ('WD_MN', 'Вывод денег со счета'), ('BRK_CM', 'Брокерская комиссия'), ('ERR', 'Ошибка')], max_length=10),
        ),
        migrations.AlterField(
            model_name='sharedeal',
            name='type_of_deal',
            field=models.CharField(choices=[('BUY_SR', 'Покупка акций'), ('SL_SR', 'Продажа акций'), ('DIV', 'Выплата дивидендов/купонов'), ('BUY_BND', 'Покупка облигаций'), ('SL_BND', 'Продажа облигаций'), ('RFL_MN', 'Внесение денег на счет'), ('WD_MN', 'Вывод денег со счета'), ('BRK_CM', 'Брокерская комиссия'), ('ERR', 'Ошибка')], max_length=10),
        ),
        migrations.CreateModel(
            name='InvestRecommendationAuthor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterField(
            model_name='investrecommendation',
            name='author',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='History.investrecommendationauthor'),
        ),
    ]