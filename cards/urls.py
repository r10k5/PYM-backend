from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("kp", views.write_kp, name="kp"),
    path("create-session", views.create_session, name="create-session"),
    path("check-session/<str:uid>", views.check_to_session, name="check-session"),
    path("connect-session/<str:uid>", views.connect_to_session, name="connect-session"),
    path("get-session/<str:uid>", views.get_session, name="get-session")
]