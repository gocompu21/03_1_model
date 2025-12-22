from django.urls import path
from . import views

app_name = "mock_exam"

urlpatterns = [
    path("", views.index, name="index"),
    path("generate/", views.generate_mock_exam, name="generate"),
    path("take/<int:pk>/", views.take_exam, name="take"),
    path("submit/<int:pk>/", views.submit_exam, name="submit"),
    path("result/<int:pk>/", views.result_exam, name="result"),
]
