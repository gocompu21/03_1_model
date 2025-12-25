from django.urls import path
from . import views

app_name = "study"

urlpatterns = [
    path("", views.index, name="index"),
    path("<int:round_number>/", views.detail, name="detail"),
    path("subject/<str:subject_name>/", views.subject_detail, name="subject_detail"),
    path("tts/", views.tts_generate, name="tts_generate"),
]
