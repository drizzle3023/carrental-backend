# Generated by Django 3.0.1 on 2020-01-29 18:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CarRentalApp', '0002_auto_20200130_0123'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='access_token',
            field=models.CharField(max_length=200, null=True),
        ),
    ]