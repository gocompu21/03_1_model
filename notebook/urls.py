from django.urls import path
from . import views

app_name = "notebook"

urlpatterns = [
    path("", views.index, name="index"),
    path("api/ask/", views.api_ask, name="api_ask"),
]
