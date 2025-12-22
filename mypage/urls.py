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
    path(
        "delete_my_question/<int:pk>/",
        views.delete_my_question,
        name="delete_my_question",
    ),
    path(
        "update_my_question/<int:pk>/",
        views.update_my_question,
        name="update_my_question",
    ),
    # Smart Review Session
    path("review/start/", views.review_start, name="review_start"),
    path("review/submit/", views.review_submit, name="review_submit"),
]
