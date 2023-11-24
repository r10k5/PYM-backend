from django.db import models

class Genre(models.Model):
    name = models.CharField(max_length=100)

class Type(models.Model):
    name = models.CharField(max_length=100)

class Card(models.Model):
    name = models.CharField(max_length=255)
    filename = models.CharField(max_length=512)
    description = models.TextField(null=True)
    rate = models.DecimalField(max_digits=3, decimal_places=2, null=True)
    genres = models.ManyToManyField(Genre)
    types = models.ManyToManyField(Type)
    year = models.IntegerField(null=True)
    duration_all = models.IntegerField(null=False, default=0)
    duration_series = models.IntegerField(null=False, default=0)
    count_series = models.IntegerField(null=False, default=0)
    kp_id = models.IntegerField(null=False, unique=True)



