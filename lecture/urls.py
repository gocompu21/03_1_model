from django.urls import path

from . import views

app_name = "lecture"

urlpatterns = [
    path("", views.index, name="index"),
    path("watch/<int:lecture_id>/", views.watch, name="watch"),
    path("manage/", views.manage, name="manage"),
    path("stats/", views.stats, name="stats"),
]
