from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("", views.index, name="index"),
    path("api/ask/", views.chat_api, name="api_ask"),
]
