from django.urls import path
from . import views

app_name = "bbs"

urlpatterns = [
    path("", views.post_list, name="post_list"),
    path("<int:pk>/", views.post_detail, name="post_detail"),
    path("create/", views.post_create, name="post_create"),
    path("<int:pk>/update/", views.post_update, name="post_update"),
    path("<int:pk>/delete/", views.post_delete, name="post_delete"),
    path("<int:pk>/comment/create/", views.comment_create, name="comment_create"),
    path("comment/<int:pk>/delete/", views.comment_delete, name="comment_delete"),
]
