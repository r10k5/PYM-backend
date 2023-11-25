from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("kp", views.write_kp, name="kp"),
]