# Generated by Django 3.0.1 on 2019-12-31 00:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CarRentalApp', '0013_auto_20191231_0614'),
    ]

    operations = [
        migrations.CreateModel(
            name='FileUploadTest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('video_file', models.FileField(upload_to='')),
                ('remark', models.CharField(max_length=20)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
