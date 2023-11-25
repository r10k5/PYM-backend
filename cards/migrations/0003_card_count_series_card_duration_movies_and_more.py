# Generated by Django 4.2.6 on 2023-11-24 15:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cards', '0002_card_year_alter_card_description_alter_card_rate'),
    ]

    operations = [
        migrations.AddField(
            model_name='card',
            name='count_series',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='card',
            name='duration_movies',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='card',
            name='duration_series',
            field=models.IntegerField(default=0),
        ),
    ]