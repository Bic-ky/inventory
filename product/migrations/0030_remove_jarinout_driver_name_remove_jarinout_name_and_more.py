# Generated by Django 5.1.1 on 2025-01-11 19:36

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0029_remove_customer_is_monthly_customer_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='jarinout',
            name='driver_name',
        ),
        migrations.RemoveField(
            model_name='jarinout',
            name='name',
        ),
        migrations.RemoveField(
            model_name='jarinout',
            name='timestamp',
        ),
        migrations.RemoveField(
            model_name='jarinout',
            name='vehicle_number',
        ),
        migrations.AlterField(
            model_name='jarinout',
            name='fillers',
            field=models.ForeignKey(blank=True, help_text='Contact person filling the jars.', null=True, on_delete=django.db.models.deletion.SET_NULL, to='product.filler'),
        ),
    ]
