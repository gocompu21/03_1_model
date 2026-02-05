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
    path(
        "wrong_answers/<int:attempt_id>/",
        views.wrong_answer_full_list,
        name="wrong_answer_full_list",
    ),
    path(
        "api/next_wrong_answers/<int:pk>/",
        views.next_wrong_answers_api,
        name="next_wrong_answers_api",
    ),
    path(
        "api/my_questions/",
        views.my_questions_api,
        name="my_questions_api",
    ),
    path(
        "api/next_questions/<int:pk>/",
        views.next_questions_api,
        name="next_questions_api",
    ),
    path("questions/", views.my_questions_list, name="my_questions_list"),
    path("history/", views.exam_history_list, name="exam_history_list"),
    path("api/exam_history/", views.exam_history_api, name="exam_history_api"),
    path("wrong-answers/", views.wrong_answer_list, name="wrong_answer_list"),
    path("member-info/", views.member_info, name="member_info"),
    path("ai-analysis/", views.ai_analysis_page, name="ai_analysis_page"),
    path("analysis/", views.analysis_page, name="analysis_page"),
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
    path("review/", views.review_index, name="review_index"),
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
    path("admin/save-infographic/", views.save_infographic_api, name="save_infographic_api"),
    path("admin/check-infographic-status/", views.check_infographic_status_api, name="check_infographic_status_api"),
    # Batch Job for Exam Questions
    path("admin/batch-job/", views.batch_job_page, name="batch_job_page"),
    path("admin/batch-job/questions/", views.batch_job_get_questions, name="batch_job_get_questions"),
    path("admin/batch-job/process/", views.batch_job_process, name="batch_job_process"),
    # Practice Question Input (CSV)
    path("admin/practice-input/books/", views.practice_input_get_books, name="practice_input_get_books"),
    path("admin/practice-input/parse/", views.practice_input_parse_csv, name="practice_input_parse_csv"),
    path("admin/practice-input/save/", views.practice_input_save, name="practice_input_save"),
    path("admin/practice-input/check-similarity/", views.practice_input_check_similarity, name="practice_input_check_similarity"),
    path("admin/practice-input/textbook-explanation/", views.practice_input_get_textbook_explanation, name="practice_input_get_textbook_explanation"),
    # Practice Question Management (Edit/Delete)
    path("admin/practice-input/questions/", views.practice_input_get_questions, name="practice_input_get_questions"),
    path("admin/practice-input/update/", views.practice_input_update_question, name="practice_input_update_question"),
    path("admin/practice-input/delete/", views.practice_input_delete_question, name="practice_input_delete_question"),
    # Chapter Tree Management
    path("admin/chapter-list/", views.chapter_list_api, name="chapter_list_api"),
    path("admin/chapter-create/", views.chapter_create, name="chapter_create"),
    path("admin/chapter-update/<int:chapter_id>/", views.chapter_update, name="chapter_update"),
    path("admin/chapter-delete/<int:chapter_id>/", views.chapter_delete, name="chapter_delete"),
    path("admin/chapter-move/<int:chapter_id>/", views.chapter_move, name="chapter_move"),
]
