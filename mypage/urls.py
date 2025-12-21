from django.urls import path
from . import views

app_name = "mypage"

urlpatterns = [
    path("", views.index, name="index"),
    path("edit/", views.edit, name="edit"),
    path("detail_answer/<int:pk>/", views.detail_answer, name="detail_answer"),
    path(
        "wrong_answer/<int:pk>/", views.wrong_answer_detail, name="wrong_answer_detail"
    ),
    path("analyze/", views.analyze_questions, name="analyze_questions"),
    path(
        "api/analyze_attempt/<int:attempt_id>/",
        views.analyze_attempt_wrong_answers,
        name="analyze_attempt_wrong_answers",
    ),
    path(
        "api/delete_attempt/<int:attempt_id>/",
        views.delete_attempt,
        name="delete_attempt",
    ),
]
