# Generated by Django 5.1.1 on 2025-01-06 16:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0024_alter_jarinout_time'),
    ]

    operations = [
        migrations.RenameField(
            model_name='jarinout',
            old_name='name',
            new_name='driver_name',
        ),
    ]