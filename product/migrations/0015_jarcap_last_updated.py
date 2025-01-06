# Generated by Django 5.1.1 on 2024-12-23 18:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0014_jarcap_usage_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='jarcap',
            name='last_updated',
            field=models.DateField(blank=True, help_text='Date when we last changed this jar cap stock.', null=True),
        ),
    ]
