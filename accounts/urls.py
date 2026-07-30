from django.urls import path
from . import views
from . import attendance

app_name = "accounts"

urlpatterns = [
    path("signup/", views.user_signup, name="user_signup"),
    path("login/", views.user_login, name="user_login"),
    path("logout/", views.user_logout, name="user_logout"),
    path("password_reset/", views.password_reset_request, name="password_reset"),
    path("heartbeat/", views.session_heartbeat, name="session_heartbeat"),
    # 출석 관리
    path("attendance/admin/", attendance.admin_attendance, name="admin_attendance"),
    path("attendance/qr.png", attendance.attendance_qr_png, name="attendance_qr_png"),
    path("attendance/check/", attendance.attendance_check, name="attendance_check"),
    path("attendance/my/", attendance.my_attendance, name="my_attendance"),
]
