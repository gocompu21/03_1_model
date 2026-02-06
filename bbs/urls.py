from django.urls import path
from . import views

app_name = "bbs"

urlpatterns = [
    path("", views.post_list, name="post_list"),
    path("api/posts/", views.post_list_api, name="post_list_api"),
    path("<int:pk>/", views.post_detail, name="post_detail"),
    path("create/", views.post_create, name="post_create"),
    path("<int:pk>/update/", views.post_update, name="post_update"),
    path("<int:pk>/delete/", views.post_delete, name="post_delete"),
    path("<int:pk>/comment/create/", views.comment_create, name="comment_create"),
    path("comment/<int:pk>/delete/", views.comment_delete, name="comment_delete"),
    path("<int:pk>/related/api/", views.related_posts_api, name="related_posts_api"),
    path("image/upload/", views.image_upload, name="image_upload"),
]
