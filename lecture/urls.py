from django.urls import path

from . import views

app_name = "lecture"

urlpatterns = [
    path("", views.index, name="index"),
    path("manage/", views.manage, name="manage"),
]
