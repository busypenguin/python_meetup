# Generated by Django 4.1.5 on 2024-11-26 09:30

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='active',
            field=models.BooleanField(default=False, verbose_name='Готов/не готов к общению'),
        ),
        migrations.AlterField(
            model_name='donate',
            name='donated_at',
            field=models.DateTimeField(default=datetime.datetime(2024, 11, 26, 9, 30, 18, 529020, tzinfo=datetime.timezone.utc), verbose_name='Время доната'),
        ),
    ]
