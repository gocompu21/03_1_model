from django.urls import path

from . import views

app_name = "treeid"

urlpatterns = [
    path("memorize/", views.memorize, name="memorize"),
    path("api/bookmark/", views.bookmark, name="bookmark"),
]
