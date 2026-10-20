from django.urls import path

from . import views

app_name = "poll"

urlpatterns = [
    path("", views.index, name="index"),
    path("done/", views.done, name="done"),
    path("manage/", views.manage, name="manage"),
    path("manage/csv/", views.export_csv, name="export_csv"),
    path("manage/delete/<int:pk>/", views.delete, name="delete"),
]
