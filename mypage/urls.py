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
    # Admin Prompt Generator
    path("admin/prompt-generator/", views.prompt_generator, name="prompt_generator"),
    path("admin/query-ai/", views.query_ai_api, name="query_ai_api"),
    path("admin/generate-narration/", views.generate_narration_api, name="generate_narration_api"),
    path("admin/save-narration/", views.save_narration_api, name="save_narration_api"),
    path("admin/generate-tts/", views.generate_tts_api, name="generate_tts_api"),
    path("admin/get-existing-tts/", views.get_existing_tts_api, name="get_existing_tts_api"),
    path("admin/generate-infographic/", views.generate_infographic_api, name="generate_infographic_api"),
]
