from django.urls import path
from . import views

app_name = "main"

urlpatterns = [
    path("", views.index, name="index"),
    path("dvd/", views.dvd, name="dvd"),
]
