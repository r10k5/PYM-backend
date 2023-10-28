from django.db import models

class Genre(models.Model):
    name = models.CharField(max_length=100)

class Type(models.Model):
    name = models.CharField(max_length=100)

class Card(models.Model):
    name = models.CharField(max_length=255)
    filename = models.CharField(max_length=512)
    description = models.TextField()
    rate = models.DecimalField(max_digits=3, decimal_places=2)
    genres = models.ManyToManyField(Genre)
    types = models.ManyToManyField(Type)


