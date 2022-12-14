# Generated by Django 4.0.3 on 2022-09-20 19:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('History', '0003_historicalsharedeal_historicalshare_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ImportBrockerDataLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('datetime', models.DateTimeField()),
                ('file_or_content', models.FileField(upload_to='brocker_data_log/')),
                ('status_code', models.IntegerField()),
                ('error_text', models.TextField()),
                ('bill', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='History.bill')),
            ],
        ),
    ]
