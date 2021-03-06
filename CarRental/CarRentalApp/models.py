from django.db import models

# Create your models here.

class User(models.Model):

    email = models.CharField(max_length=200, blank=True)

    # sms-entry
    user_id = models.CharField(max_length=200)
    mobile = models.CharField(max_length=50)
    name = models.CharField(max_length=200, null = True)

    car_type_id = models.IntegerField(null = True)
    world_zone = models.CharField(max_length=200, null = True, blank=True)
    user_app_id = models.CharField(max_length=200, null = True, blank=True)

    namespace = models.CharField(max_length=200, null = True)
    confirmation_hash = models.CharField(max_length=200, null = True)
    created_at = models.DateTimeField(auto_now_add = True)
    href = models.CharField(max_length=200, null = True)
    target_id = models.CharField(max_length=200, null = True)
    type = models.CharField(max_length=200, null = True)
    updated_at = models.DateTimeField(auto_now = True)

    # sms-verify
    access_token = models.CharField(max_length=200, null = True)
    client_id = models.CharField(max_length=200, null = True)
    code = models.CharField(max_length=200, null = True)
    endpoints_http = models.CharField(max_length=200, null = True)
    endpoints_mqtt = models.CharField(max_length=200, null = True)
    endpoints_uploader = models.CharField(max_length=200, null = True)
    expires_at = models.DateTimeField(blank=True, null = True)
    grant_type = models.CharField(max_length=200, null = True)
    href = models.CharField(max_length=200, null = True)
    owner_id = models.CharField(max_length=200, null = True)
    refresh_token = models.CharField(max_length=200, null = True)
    scope_1 = models.CharField(max_length=200, null = True)
    scope_2 = models.CharField(max_length=200, null = True)
    pay_state = models.IntegerField(null = True, blank=True)

class Coverage(models.Model):

    name = models.CharField(max_length=200, null = True)
    user_id = models.IntegerField(null = True, blank=True)
    latitude = models.FloatField(null = True)
    longitude = models.FloatField(null = True)
    address = models.CharField(max_length=200, blank=True, null = True)
    company_id = models.IntegerField(null = True)
    starting_at = models.DateTimeField(blank=True, null = True)
    ending_at = models.DateTimeField(blank=True, null = True)
    video_mile = models.FileField(blank=True, null = True)
    video_vehicle = models.FileField(blank=True, null = True)
    image_mile = models.FileField(blank=True, null = True)
    image_vehicle = models.FileField(blank=True, null = True)
    state = models.IntegerField(blank=True, null = True)   # COVERED: 1, UNCOVERED: 2
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

class Company(models.Model):

    name = models.CharField(max_length=200)
    type = models.CharField(max_length=200, null = True)
    latitude = models.FloatField(null = True)
    longitude = models.FloatField(null = True)
    address = models.CharField(max_length=200, blank=True, null = True)
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

class CarType(models.Model):

    name = models.CharField(max_length=200)
    icon_url = models.FileField(null = True)
    price_per_year_usd = models.FloatField(default=0)
    price_per_year_eur = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

class Claim(models.Model):

    name = models.CharField(max_length=200, null = True)
    user_id = models.IntegerField(blank = True, null = True)
    coverage_id = models.IntegerField()
    what_happened = models.CharField(max_length=200)
    date_time_happened = models.DateTimeField(null = True)
    time_happened = models.BigIntegerField(null = True)
    latitude = models.FloatField(blank=True, null = True)
    longitude = models.FloatField(blank = True, null = True)
    address = models.CharField(max_length=200, blank = True, null = True)
    damaged_part = models.CharField(max_length=1000, blank=True, null=True)
    video = models.FileField(blank = True, null = True)
    image = models.FileField(blank = True, null = True)
    note = models.CharField(max_length=200, blank = True, null = True)
    state = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

class Payment(models.Model):

    user_id = models.IntegerField()
    car_type_id = models.IntegerField()
    amount = models.FloatField()
    currency = models.CharField(max_length=200)
    state = models.IntegerField(null = True)
    date = models.DateTimeField(auto_now_add = True)
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

class History(models.Model):

    user_id = models.IntegerField()
    type = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

class FileUploadTest(models.Model):

    video_file = models.FileField(blank=False, null = False)
    remark = models.CharField(max_length=20)
    timestamp = models.DateTimeField(auto_now_add=True)

class Support(models.Model):
    phone_number = models.CharField(max_length=100)