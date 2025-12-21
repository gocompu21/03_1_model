from django.urls import path
from . import views

app_name = "mypage"

urlpatterns = [
    path("", views.index, name="index"),
    path("edit/", views.edit, name="edit"),
    path("detail_answer/<int:pk>/", views.detail_answer, name="detail_answer"),
]
