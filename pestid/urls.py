from django.urls import path

from . import views

app_name = "pestid"

urlpatterns = [
    path("", views.index, name="index"),
    path("play/<int:course_id>/", views.play, name="play"),
    path("api/grade/", views.grade, name="grade"),
    path("api/finish/", views.finish, name="finish"),
]
