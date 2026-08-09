from django.urls import path

from . import views

app_name = "dvdexam"

urlpatterns = [
    path("", views.index, name="index"),
    path("manage/", views.manage, name="manage"),
    path("<int:exam_id>/", views.take, name="take"),
    path("<int:exam_id>/save/", views.save, name="save"),
    path("<int:exam_id>/submit/", views.submit, name="submit"),
    path("<int:exam_id>/result/", views.result, name="result"),
    path("<int:exam_id>/overview/", views.overview, name="overview"),
    path("<int:exam_id>/review/", views.review, name="review"),
    path("<int:exam_id>/scores/", views.scores, name="scores"),
    path("<int:exam_id>/scores/api/", views.scores_api, name="scores_api"),
]
