from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.user_signup, name="user_signup"),
    path("login/", views.user_login, name="user_login"),
    path("logout/", views.user_logout, name="user_logout"),
    path("password_reset/", views.password_reset_request, name="password_reset"),
]
