# Generated by Django 5.1.1 on 2024-12-06 06:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0003_bill'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='delivery',
            name='status',
        ),
        migrations.AddField(
            model_name='delivery',
            name='delivered_count',
            field=models.IntegerField(default=0, help_text='Number of jars successfully delivered'),
        ),
        migrations.AddField(
            model_name='delivery',
            name='half_caps_count',
            field=models.IntegerField(default=0, help_text='Number of jars with half caps issues'),
        ),
        migrations.AddField(
            model_name='delivery',
            name='leak_count',
            field=models.IntegerField(default=0, help_text='Number of jars found leaking'),
        ),
        migrations.AddField(
            model_name='delivery',
            name='returned_count',
            field=models.IntegerField(default=0, help_text='Number of jars returned by the customer'),
        ),
    ]
